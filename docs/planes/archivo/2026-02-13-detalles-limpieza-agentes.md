# Plan de Limpieza de Agentes (Fase 1) - v0.8.2

> **Estado:** Completado ✅
> **Fecha:** 2026-02-15
> **Objetivo:** Eliminar código muerto y archivos huérfanos en `src/agents/` para preparar el terreno para la arquitectura de Skills (OpenClaw).

## 1. Contexto
El análisis de `src/agents/` reveló un ~12% de código muerto o no utilizado. Este código añade carga cognitiva y complejidad innecesaria. Antes de implementar el sistema de Skills (Bloque C del Roadmap), es crucial sanear el directorio.

## 2. Alcance de la Limpieza

### A. Archivos Huérfanos (Eliminados)
Estos archivos no eran importados ni utilizados en ninguna parte del proyecto:
1.  `src/agents/config.py` (Clase `AgentConfig` no usada)
2.  `src/agents/file_readers.py` (Registro de lectores no usado)
3.  `src/agents/file_validators.py` (Validadores no usados)
4.  `src/agents/utils/history_tool.py` (Herramienta no registrada)
5.  `src/agents/workflows/` (Directorio completo, incluyendo `base_workflow.py` y `research/`)

### B. Código Muerto en Archivos Activos (Editados)
Funciones definidas pero nunca invocadas han sido removidas:
1.  `src/agents/orchestrator/graph_builder.py`: Método `_validate_routing_functions` eliminado.
2.  `src/agents/orchestrator/routing/routing_prompts.py`: Función `build_fallback_context_message` eliminada.

### C. Interfaces Núcleo sin Uso (Eliminadas)
Interfaces en `src/core/interfaces/` que no tenían implementaciones ni referencias:
1.  `src/core/interfaces/modular_agent.py` (Diseño abandonado)
2.  `src/core/interfaces/tool.py` (Interfaz `ITool` no usada, se usa `BaseTool` de LangChain)
3.  `src/core/interfaces/workflow.py` (Interfaz `IWorkflow` duplicada y no usada)

### D. Limpieza de Cache
1.  Eliminados archivos `.pyc` huérfanos en `src/agents/__pycache__/` y subdirectorios.

### E. Mantenimiento Adicional
1.  Se corrigieron tipos faltantes en `src/core/logging/types.py` (`LoggersConfig`, `LoggingDictConfiguration`) que causaban errores silenciosos en análisis estático.

## 3. Plan de Ejecución
1.  **Validación Previa:** Ejecutada (con correcciones de linting en `src/core`).
2.  **Eliminación:** Completada.
3.  **Edición:** Completada.
4.  **Validación Post-Limpieza:** `make verify` pasó exitosamente (137 tests OK, linting OK).

## 4. Criterios de Éxito
- [x] Reducción de ~450 LOC.
- [x] `make verify` pasa exitosamente.
- [x] No hay errores de importación en el arranque del servicio.
