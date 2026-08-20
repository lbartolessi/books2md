#!/usr/bin/env python3
"""Script interactivo para sincronizar recursivamente docstrings en un paquete de Python.

Recorre recursivamente un directorio objetivo, localiza todos los archivos .py
(incluyendo __init__.py) y procesa cada uno con la API de Gemini tras solicitar
confirmación interactiva al usuario.
"""

import os
import sys
from pathlib import Path

import google.genai as genai
from google.genai import types

# Define la plantilla del prompt basada en tus directivas arquitectónicas
PROMPT_TEMPLATE = """# Role: Technical Documentation Architect & Knowledge Extractor

## THE MISSION
You are an expert technical archiver and systems analyst. Your task is to perform an exhaustive audit of provided source code to generate high-fidelity, machine-readable, and human-accessible documentation. You are not writing code; you are extracting the implicit logic and architectural intent from fully implemented Python modules to facilitate their discovery by future developers and autonomous AI agents.

---

## THE ULTIMATE PURPOSE
The docstrings you generate must be 100% self-sufficient. An external AI agent reading these docstrings must be able to understand the exact behavior, edge cases, and constraints of the module, class, or method without needing to parse the function body. You are upgrading legacy or undocumented code into "Self-Documenting Architectural Assets."

---

## THE GLOBAL ARCHITECTURAL DIRECTIVES
1. Integrated Documentation Hierarchy: You must provide documentation at three levels:
   - Module Level: Teleological summary, core responsibilities, and key dependencies.
   - Class Level: Behavioral definition, initialization requirements, and internal state management.
   - Method/Function Level: Detailed I/O, exceptions, mutations, and internal logic constraints.
2. Reverse Engineering Extraction: Do not guess the intent. Analyze the actual implementation. If the code uses a constant (e.g., LIMIT = 55), the docstring MUST explicitly state: "Threshold limit: 55" and not simply "The limit is configurable."
3. Integration Policy: If existing docstrings exist, you must merge them with your new, deeper analysis, preserving the previous context while upgrading the technical precision to meet Google Style requirements.
4. Code Isomorphism: You have ZERO authorization to alter the code logic, imports, variable names, or signatures. Every import, class definition, function signature, and internal variable must remain character-for-character identical to the input. Only docstrings and comment blocks may be inserted or expanded.

---

## EXECUTION RULES (STRICT)
1. MANDATORY ANALYTICAL BLUEPRINT:
   The very first thing you output must be an "Analytical Blueprint". List every Module, Class, and Function you have analyzed, briefly summarizing the logic/pattern you extracted from their implementation.
2. HERMETIC UNPACKING CONTRACT:
   You are forbidden from using abstract terms (e.g., "processes the data", "checks constraints", "validates inputs"). You MUST unpack these into actionable logic.
3. MUTATION DECLARATION:
   You must explicitly declare if a method performs structural modifications (in-place) to the BeautifulSoup/DOM object or class state. If it is a read-only operation, state "None".
4. DOM/STATE EDGE CASES:
   Every docstring must explicitly declare handling for Node/Type Safety and Null/Early Returns.

---

## TARGET FORMAT
For every artifact, format docstrings utilizing strict Google Style:

\"\"\"[Clear teleological definition: What is the purpose of this object?]

Attributes:
    [attr_name] ([type]): [Brief description of state variable]

Args:
    [param_name] ([type]): [Description, including preconditions, type safety, and null handling]

Returns:
    [type]: [Description of returned value and criteria for early-returns/fallbacks]

Raises:
    [ExceptionType]: [Document requirements to catch/log/re-raise]

Mutations:
    [Explicitly describe in-place DOM modifications or state changes here. If none, state 'None'.]

Rules & Logic:
    [Explicitly state numerical thresholds, regex patterns, or conditional branches extracted from the code.]
\"\"\"

---

## OUTPUT FORMAT REQUIREMENTS
1. First, provide the Analytical Blueprint.
2. Second, provide a single code block ```python ... ``` containing the ENTIRE updated source code. Do not truncate or use placeholders like "... rest of code ...".

---

## SOURCE CODE TO DOCUMENT

```python
{source_code}

```

"""

def collect_python_files(target_dir: Path) -> list[Path]:
    """Recoge recursivamente todos los archivos .py dentro de un directorio."""
    return sorted([p for p in target_dir.rglob("*.py") if p.is_file()])

def extract_code_block(response_text: str) -> str | None:
    """Extrae el contenido del bloque de código python devuelto por el modelo."""
    if "`python" in response_text:
        parts = response_text.split("`python")
        if len(parts) > 1:
            code_part = parts[1].split("`")[0]
            return code_part.strip()
        elif "`" in response_text:
            parts = response_text.split("```")
            if len(parts) > 1:
                return parts[1].strip()
    return None

def print_usage():
    """Imprime el mensaje de uso del script."""
    print("Uso: python sync_docstrings.py <directorio_de_fuentes>")
    print("Ejemplo: python sync_docstrings.py packages/dom_normalizer/src")

def process_file_with_gemini(client: genai.Client, file_path: Path) -> bool:
    """Envía el código fuente a Gemini para actualizar sus docstrings."""
    print("\n" + "=" * 80)
    print(f"📄 Procesando: {file_path}")
    print("=" * 80)

    try:
        source_code = file_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"❌ Error al leer el archivo {file_path}: {e}")
        return False

    prompt = PROMPT_TEMPLATE.format(source_code=source_code)

    print("🤖 Generando documentación con Gemini...")
    try:
        # Se utiliza gemini-2.5-flash para obtener respuestas rápidas y de alta calidad
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(),
        )
    except Exception as e:
        print(f"❌ Error durante la llamada a la API de Gemini: {e}")
        return False

    response_text = response.text
    if response_text is None:
        print("❌ Respuesta vacía de Gemini.")
        return False
    new_code = extract_code_block(response_text)

    # Imprimir el análisis previo (Analytical Blueprint)
    print("\n--- ANALYTICAL BLUEPRINT ---")
    blueprint_part = response_text.split("```")[0] if "```" in response_text else response_text
    print(blueprint_part.strip())
    print("----------------------------\n")

    if not new_code:
        print("⚠️ No se pudo extraer un bloque de código válido de la respuesta de Gemini.")
        print("Respuesta recibida:")
        print(f"{response_text[:500]}...")
        return False

    # Guardar cambios
    try:
        file_path.write_text(new_code + "\n", encoding="utf-8")
        print(f"✅ Archivo actualizado con éxito: {file_path}")
        return True
    except Exception as e:
        print(f"❌ Error al escribir los cambios en {file_path}: {e}")
        return False


def main():
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)


    target_dir = Path(sys.argv[1]).resolve()
    if not target_dir.exists() or not target_dir.is_dir():
        print(f"❌ El directorio especificado no existe o no es válido: {target_dir}")
        sys.exit(1)

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("❌ La variable de entorno GEMINI_API_KEY no está configurada.")
        print("Por favor, ejecute: export GEMINI_API_KEY='tu_api_key'")
        sys.exit(1)

    client = genai.Client(api_key=api_key)
    py_files = collect_python_files(target_dir)

    if not py_files:
        print(f"No se encontraron archivos .py en: {target_dir}")
        sys.exit(0)

    print(f"Encontrados {len(py_files)} archivos .py en {target_dir}:\n")
    for idx, f in enumerate(py_files, 1):
        rel_path = f.relative_to(target_dir)
        print(f"  {idx}. {rel_path}")

    print("\nIniciando proceso interactivo...\n")

    processed_count = 0
    skipped_count = 0

    for f in py_files:
        rel_path = f.relative_to(target_dir)

        # Bucle de interacción explícita
        while True:
            choice = input(f"\n¿Procesar '{rel_path}'? [s (sí) / n (saltar) / q (salir)]: ").strip().lower()
            if choice in ['s', 'si', 'y', 'yes']:
                success = process_file_with_gemini(client, f)
                if success:
                    processed_count += 1
                break
            elif choice in ['n', 'no']:
                print(f"⏭️ Omitiendo: {rel_path}")
                skipped_count += 1
                break
            elif choice in ['q', 'quit', 'exit']:
                print("\nSaliendo del proceso a petición del usuario.")
                print(f"Resumen: {processed_count} procesados, {skipped_count} omitidos.")
                sys.exit(0)
            else:
                print("Por favor, responde 's' para procesar, 'n' para saltar o 'q' para salir.")

    print(f"\n🎉 Proceso completado. Archivos procesados: {processed_count}, Omitidos: {skipped_count}.")



if __name__ == "__main__":
    main()
