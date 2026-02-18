# Plan de Refactorización y Eliminación de Deuda Técnica

> **Estado:** Borrador
> **Fecha:** 17 Feb 2026
> **Objetivo:** Eliminar la deuda técnica remanente (complejidad ciclomática, extensión de archivos/funciones, tipado incompleto) para alcanzar un cumplimiento estricto del 100% con los estándares de AEGEN v0.8.0.

## 1. Resumen Ejecutivo

Tras la fase de remediación crítica (seguridad y linter base), el proyecto mantiene una deuda técnica "soft" que no bloquea la ejecución pero afecta la mantenibilidad a largo plazo. Este plan estructura la intervención en **45 archivos** para resolver violaciones de extensión, tipado y estilo.

**Métricas de Deuda Actual:**
- **Funciones Extensas (>50 líneas):** 23 funciones en 15 archivos.
- **Archivos Extensos (>200 líneas):** 5 archivos críticos del Core.
- **Tipado Incompleto (Mypy):** ~90 advertencias (falta de `-> None` y `cast`).
- **Estilo (E501):** ~100 líneas largas en logs/prompts.

---

## 2. Estrategia de Ejecución (Sprints Técnicos)

La refactorización se dividirá en 3 fases lógicas para minimizar el riesgo de regresión, priorizando los componentes más propensos a cambios (Agentes y Core).

### Fase 1: Modularización del Core (Alta Prioridad)
*Objetivo: Reducir la complejidad en los gestores de estado y perfil.*

**Archivos Objetivo:**
1.  `src/core/profile_manager.py` (220 líneas) -> Extraer validaciones y seeding a `profile_service.py` o mixins.
2.  `src/core/session_manager.py` (241 líneas) -> Mover lógica de consolidación a `session_consolidation.py`.
3.  `src/core/observability/handler.py` (235 líneas) -> Separar métricas de logging.
4.  `src/agents/orchestrator/routing/routing_utils.py` (206 líneas) -> Dividir utilidades de parsing y validación.

**Acciones:**
- Extraer clases auxiliares o funciones privadas.
- Asegurar cobertura de tests antes de refactorizar.
- Validar con `simple_check.py` que los archivos bajen de 200 líneas.

### Fase 2: Desacoplamiento de Agentes (Media Prioridad)
*Objetivo: Simplificar las herramientas de los especialistas, que actualmente contienen lógica de negocio mezclada con definiciones.*

**Archivos Objetivo:**
1.  `src/agents/specialists/chat/chat_tool.py` (Función `conversational_chat_tool` de 130 líneas).
2.  `src/agents/specialists/cbt/cbt_tool.py` (Función `cbt_therapeutic_guidance_tool` de 120 líneas).
3.  `src/personality/prompt_builder.py` (228 líneas).

**Acciones:**
- Separar la definición de la herramienta (`tool`) de la lógica de ejecución (`runner`).
- Mover los prompts largos a archivos de texto/yaml externos o módulos de constantes (`prompts.py`).
- Implementar patrón Strategy si hay múltiples flujos dentro de la herramienta.

### Fase 3: Tipado Estricto y Pulido (Baja Prioridad / Mecánico)
*Objetivo: Alcanzar "Zero Warnings" en Mypy y Ruff.*

**Alcance:**
- **Mypy:** Agregar anotaciones de retorno `-> None` faltantes en ~30 archivos (repositorios, scripts, tests).
- **Ruff E501:** Refactorizar logs y strings largos usando concatenación implícita `("..." "...")`.
- **Scripts:** Refactorizar `process_telegram_update` en `telegram_adapter.py` (88 líneas) y `setup_logging` en `logging_config.py` (112 líneas).

---

## 3. Inventario Detallado de Deuda

### A. Violaciones de Extensión de Archivo (>200 líneas)
| Archivo | Líneas | Acción Recomendada |
|---------|--------|-------------------|
| `src/core/session_manager.py` | 241 | Extraer `SessionConsolidator` |
| `src/core/observability/handler.py` | 235 | Separar `MetricsHandler` y `LogHandler` |
| `src/personality/prompt_builder.py` | 228 | Mover templates a `src/prompts/` |
| `src/core/profile_manager.py` | 220 | Extraer `ProfileSeeder` |
| `src/agents/orchestrator/routing/routing_utils.py` | 206 | Separar `IntentParser` |

### B. Violaciones de Extensión de Función (>50 líneas)
*Top 5 Candidatos a Refactorización:*
1.  `conversational_chat_tool` (130 líneas): Lógica de flujo demasiado compleja para una sola función.
2.  `cbt_therapeutic_guidance_tool` (120 líneas): Mezcla validación, lógica TCC y formateo.
3.  `setup_logging` (112 líneas): Configuración monolítica.
4.  `process_telegram_update` (88 líneas): Parsing y routing mezclados.
5.  `search` (86 líneas en `hybrid_search.py`): Lógica de ranking y fusión compleja.

---

## 4. Criterios de Aceptación Final

1.  **Arquitectura:** Ningún archivo de lógica > 200 líneas.
2.  **Complejidad:** Ninguna función > 50 líneas (Soft limit).
3.  **Tipado:** `mypy` pasa con 0 errores en modo estricto (sin overrides masivos).
4.  **Linter:** `ruff` pasa con 0 errores (incluyendo E501 y estilos).
5.  **Tests:** Cobertura mantenida > 60% y suite pasando al 100%.

## 5. Procedimiento de Trabajo

1.  Crear branch `refactor/technical-debt`.
2.  Ejecutar `make verify` antes de empezar para tener línea base.
3.  Abordar Fase 1 (Core) -> Commit -> PR.
4.  Abordar Fase 2 (Agentes) -> Commit -> PR.
5.  Abordar Fase 3 (Tipado) -> Commit -> PR.
6.  Merge a `develop`.
