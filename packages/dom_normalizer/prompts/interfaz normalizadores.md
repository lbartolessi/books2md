# 1. Resumen Ejecutivo

El proyecto `dom_normalizer` presenta una arquitectura ambiciosa orientada a estrategias, pero sufre de una **fragmentación excesiva en el directorio `core/`** y una **falta de abstracción clara** en la ejecución de la pipeline. Existe una fuerte tendencia al acoplamiento entre los procesadores específicos y utilidades de bajo nivel, lo que dificulta la extensibilidad. La coexistencia de lógica de normalización dispersa en múltiples módulos sin una interfaz común estricta ("contrato de normalizador") genera deuda técnica. El sistema depende críticamente de la integridad del `component_registry` y del flujo de contexto, áreas que actualmente presentan señales de rigidez.

## 2. Matriz de Diagnóstico

| Severidad | Hallazgo | Impacto |
| :--- | :--- | :--- |
| **Crítico** | Ausencia de un protocolo base (`Protocol`) para normalizadores. | Inconsistencia en la ejecución y falta de tipado estricto. |
| **Alto** | Fragmentación excesiva en `core/`: mezclas de utilidades, configuración y estado. | Dificultad de mantenimiento y alta probabilidad de efectos secundarios. |
| **Alto** | Desincronización: los docstrings no reflejan la realidad de los tests `YAML`. | Erosión de la calidad del código y confusión en el desarrollo futuro. |
| **Medio** | Acoplamiento implícito entre `core/` y componentes específicos. | Riesgo de que cambios en utilidades rompan procesadores. |

---

### 3. Plan de Ejecución Modular (Fases Atómicas)

#### Paso 1: Definición del Contrato Base

**Objetivo:** Crear un protocolo (`typing.Protocol`) para asegurar que todos los normalizadores cumplan una interfaz estándar.
**Archivos afectados:** `packages/dom_normalizer/src/dom_normalizer/core/protocols.py` (nuevo)

**Prompt para copiar a Qwen:**

```text
Actúa como un desarrollador experto en Python. Tu tarea es implementar un contrato base para la librería.
Contexto de la tarea:
- Archivo a crear: packages/dom_normalizer/src/dom_normalizer/core/protocols.py
- Objetivo: Definir un `typing.Protocol` llamado `NormalizerStrategy` que defina el método `process(element: Any) -> Any` o equivalente.
Instrucciones de implementación:
1. Definir el protocolo `NormalizerStrategy` usando `typing.Protocol`.
2. Asegurar el uso de tipos abstractos correctos.
3. Incluir docstring estilo Google.
Reglas estrictas de salida:
- NO incluyas la Cadena de Razonamiento.
- NO incluyas explicaciones conversacionales.
- Genera ÚNICAMENTE el código completo del archivo.
```

#### Paso 2: Refactorización de la Pipeline Core

**Objetivo:** Centralizar la ejecución mediante la inyección del protocolo definido.
**Archivos afectados:** `packages/dom_normalizer/src/dom_normalizer/core/component_registry.py`

**Prompt para copiar a Qwen:**

```text
Actúa como un desarrollador experto en Python. Tu tarea es implementar el siguiente cambio atómico en el proyecto.
Contexto de la tarea:

- Archivo a modificar: src/dom_normalizer/strategies/**init**.py
- Objetivo: Definir un typing.Protocol llamado StrategyProtocol que declare los métodos públicos que deben implementar todas las estrategias de normalización (p.ej., `normalize(self, dom: Any) -> Any`). Añadir docstring descriptivo y anotaciones de tipos estrictas.

Instrucciones de implementación:

1. Importar `Protocol` y `runtime_checkable` de `typing`.
2. Definir `@runtime_checkable class StrategyProtocol(Protocol):` con los métodos requeridos.
3. Documentar cada método con estilo Google docstring.
4. Repetir el mismo proceso en src/dom_normalizer/analyzers/**init**.py creando AnalyzerProtocol con al menos `analyze(self, dom: Any) -> Any`.
Reglas estrictas de salida:

- NO incluyas la Cadena de Razonamiento (Chain of Thought o CoT).
- NO incluyas explicaciones conversacionales antes o después del código.
- Genera ÚNICAMENTE el código completo o el diff directo listo para aplicar.
- Genera ÚNICAMENTE el código completo del archivo refactorizado.

```

#### Paso 3: Sincronización de Documentación

**Objetivo:** Actualizar los docstrings de los normalizadores para alinearlos con las especificaciones de los tests YAML.
**Archivos afectados:** `packages/dom_normalizer/src/dom_normalizer/heading_normalizer.py`, `packages/dom_normalizer/src/dom_normalizer/footnotes/` (o similares).

**Prompt para copiar a Qwen:**

```text
Actúa como un desarrollador experto en Python. Tu tarea es sincronizar la documentación con los tests.
Contexto de la tarea:
- Archivo: [Ruta del normalizador específico]
- Objetivo: Actualizar el docstring del módulo y clases para que coincidan con el comportamiento esperado en los tests YAML (especificaciones reales).
Instrucciones de implementación:
1. Leer el docstring actual y compararlo con el comportamiento esperado (según contexto previo).
2. Reescribir el docstring estilo Google para que sea la fuente de verdad precisa.
3. Asegurar cumplimiento de `typing`.
Reglas estrictas de salida:
- NO incluyas la Cadena de Razonamiento.
- NO incluyas explicaciones conversacionales.
- Genera ÚNICAMENTE el código completo del archivo con los cambios aplicados.
```

#### Paso 4: Limpieza de Dependencias (Core)

**Objetivo:** Eliminar dependencias circulares y desacoplar `dom_utils` de los componentes.
**Archivos afectados:** `packages/dom_normalizer/src/dom_normalizer/core/dom_utils.py`

**Prompt para copiar a Qwen:**

```text
Actúa como un desarrollador experto en Python. Tu tarea es desacoplar las utilidades de DOM.
Contexto de la tarea:
- Archivo a modificar: packages/dom_normalizer/src/dom_normalizer/core/dom_utils.py
- Objetivo: Eliminar dependencias hacia componentes específicos o módulos de alto nivel.
Instrucciones de implementación:
1. Aislar las funciones de manipulación de DOM puras.
2. Eliminar cualquier importación de `dom_normalizer.footnotes` u otros sub-paquetes.
3. Asegurar que las funciones sean puramente utilitarias.
Reglas estrictas de salida:
- NO incluyas la Cadena de Razonamiento.
- NO incluyas explicaciones conversacionales.
- Genera ÚNICAMENTE el código completo del archivo refactorizado.
```
