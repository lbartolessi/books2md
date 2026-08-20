@packages/dom_normalizer

# **Prompt Maestro — Review Arquitectónico y Generación de Plan de Ejecución Atómico**

Realiza una revisión arquitectónica exhaustiva del proyecto `packages/dom_normalizer`.

Este proyecto consiste en una librería para implementar una pipeline cuyo objetivo es normalizar estructuras de DOM no normativas y a menudo semánticamente débiles (por ejemplo libros en formato epub o directorios de web scrapping)
para que Pandoc pueda procesarla y obtener de ella una representación en formato markdown.

Tiene que poder especificar diferentes estructuras (a veces no previstas) para hacer las mismas cosas (por ejemplo las notas al pie) y por eso se basa fundamentalmente en patrones strategy y análisis topológico.

Forma parte de un monorepo donde se irán añadiendo más librerías.
Considera todos los archivos del proyecto `packages/dom_normalizer` como parte de una librería que
más adelante formará parte de un sistema coherente.

Las suites de test del directorio `packages/dom_normalizer/tests/specs/dom_normalizer` en formato yaml que ejecuta el script `packages/dom_normalizer/tests/run_yaml_tests.py` son pruebas `black box`preparadas antes de escribir una sola línea de código y basándose en los docstrings. Constituyen la fuente de verdad ultima. Ha habido variaciones en las especificaciones que están recogidas en las pruebas pero los docstring no se han actualizado todavía para reflejarlas. El script `packages/dom_normalizer/tests/run_yaml_tests.py` es muy dependiente de la estructura de la librería y debe ser tenido en cuenta en cada refactorización.

**Objetivos del análisis:**

- Identificar problemas de arquitectura, diseño y organización del código.
- Evaluar cohesión, acoplamiento, modularidad y separación de responsabilidades.
- Detectar dependencias implícitas, puntos de fallo, duplicación lógica y violaciones de principios SOLID.
- Analizar la claridad de las interfaces públicas y la consistencia de los patrones utilizados.
- Señalar deuda técnica, manejo de errores y áreas de refactorización estratégica.

---

**Formato del resultado requerido:**

1. **Resumen Ejecutivo:** Diagnóstico global breve del estado del código.
2. **Matriz de Diagnóstico:** Breve lista priorizada de hallazgos por severidad (Crítico, Alto, Medio).
3. **Plan de Ejecución Modular (Fases Atómicas):**
   Divide la refactorización en una secuencia estricta de pasos pequeños, independientes y probables mediante tests.

   Para CADA PASO de la refactorización, debes generar un **Prompt para Ejecutor (Qwen-2.5-Coder-32b)** que contenga EXACTAMENTE la siguiente estructura:

   ---

   ## **Paso X: [Nombre corto de la tarea]**

   **Objetivo:** [Breve descripción de lo que se va a modificar/crear]
   **Archivos afectados:** [Ruta del archivo o archivos concretos]

   **Prompt para copiar a Qwen:**

   ```text
   Actúa como un desarrollador experto en Python. Tu tarea es implementar el siguiente cambio atómico en el proyecto.

   Contexto de la tarea:
   - Archivo a modificar: [Ruta]
   - Objetivo: [Qué hacer específicamente]

   Instrucciones de implementación:
   1. [Detalle 1: e.g., Definir la interfaz / protocolo mediante typing.Protocol]
   2. [Detalle 2: e.g., Implementar el método X manejando el caso límite Y]
   3. [Detalle 3: e.g., Asegurar docstrings tipo Google y anotaciones de tipos estrictas]

   Reglas estrictas de salida:
   - NO incluyas la Cadena de Razonamiento (Chain of Thought o CoT).
   - NO incluyas explicaciones conversacionales antes o después del código.
   - Genera ÚNICAMENTE el código completo o el diff directo listo para aplicar.

**Reglas de la respuesta:**

- NO modifiques ningún archivo.
- NO generes código completo en esta fase de análisis; limita la salida a la arquitectura y a los prompts de ejecución.
- Asegúrate de que los pasos creados sean lo suficientemente pequeños para que el modelo ejecutor no agote su cuota de tokens en una sola respuesta.
