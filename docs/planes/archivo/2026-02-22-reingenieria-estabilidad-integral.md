# PLAN: Reingeniería de Estabilidad Integral y Especialización del Motor (v1.3)

> **Instrucciones para Agentes:**
> - Para **crear** o modificar este plan: Usar la skill `writing-plans`.
> - Para **ejecutar** este plan: Usar la skill `executing-plans` para proceder tarea por tarea con verificaciones intermedias.
> - **Criterio de calidad:** Evaluar trade-offs de cada cambio respecto a: puntos únicos de fallo, degradación suave, y acoplamiento entre módulos. Aceptar complejidad solo cuando el ROI lo justifique (Principio Core #2).

- **Estado:** Completado
- **Fecha:** 2026-02-22
- **Razón de Creación:** Inestabilidad estructural detectada en producción: errores de formato JSON en memoria y fugas de regionalismos ("tío") debido a la saturación del prompt único.
- **ADR Relacionado:** adr/ADR-0028-cerebro-dual-motores-especializados.md
- **Objetivo General:** Implementar una arquitectura de Cerebro Dual que separe la lógica de sistema (JSON/Extracción) de la interfaz conversacional (MAGI), eliminando los fallos de formato y garantizando una identidad lingüística neutra y resiliente.

---

## Resumen Ejecutivo

AEGEN ha alcanzado un nivel de complejidad donde un solo modelo de lenguaje (Kimi K2) ya no puede manejar simultáneamente la profundidad empática ("Soul Stack") y la precisión técnica (JSON) sin cometer errores. Este plan introduce la especialización: el modelo `gpt-oss-120b` se encargará de la estructura y memoria (Motor Core), mientras que Kimi K2 seguirá encargándose del chat (Motor Interfaz), con un blindaje lingüístico renovado para erradicar regionalismos no deseados. Si no se ejecuta, el sistema seguirá sufriendo de "amnesia técnica" y respuestas incoherentes.

---

## Análisis de Impacto

### Dependencias afectadas
- `src/core/engine.py`: Reestructuración del singleton `llm` a `llm_chat` y `llm_core`.
- `src/personality/prompt_builder.py`: Refactorización de la clase `SystemPromptBuilder` para soportar modos técnicos.
- `src/memory/repositories/state_repo.py`: Ajuste de tipos y retornos.
- `src/api/services/event_processor.py`: Inyección de filtros post-procesamiento.

### Cobertura de tests existente
- `tests/unit/core/test_engine.py`: Debe actualizarse para probar ambos motores.
- `tests/unit/memory/test_state_repo.py`: Verificar persistencia con el nuevo contrato de datos.

### Verificación del pipeline
- Se debe trazar el flujo desde el `Polling` hasta el `ReflectionNode` asegurando que la separación de motores no genere latencias circulares.

---

## Fase 1: Arquitectura de Cerebro Dual (Engine)

### Objetivo
Establecer dos motores LLM con propósitos e instrucciones de sistema aisladas.

### Justificación
Previene que el modelo de chat afecte la integridad de la base de datos y viceversa.

### Cambios Previstos
- **Módulo/Archivo:** `src/core/engine.py`
  - **Acción:** Modificar
  - **Descripción:** Crear `llm_chat` (Kimi K2, 10s timeout, temp 0.7) y `llm_core` (gpt-oss-120b, 15s timeout, temp 0). Implementar fallback a Gemini 2.5 Flash en ambos.
- **Módulo/Archivo:** `src/core/config/base.py`
  - **Acción:** Modificar
  - **Descripción:** Agregar `GEMINI_2_5_FLASH` como modelo de RAG y respaldo global.

---

## Fase 2: Aislamiento de Prompts (Personality Sandboxing)

### Objetivo
Garantizar que las tareas técnicas reciban prompts 100% operativos sin "alma".

### Justificación
Groq/gpt-oss-120b es más preciso si no tiene que procesar 2000 tokens de "cómo ser un buen amigo" antes de extraer un JSON.

### Cambios Previstos
- **Módulo/Archivo:** `src/personality/prompt_builder.py`
  - **Acción:** Modificar
  - **Descripción:** Crear método `build_technical_prompt`. Refactorizar `build` para que acepte un flag `personality=True/False`.
- **Módulo/Archivo:** `src/personality/base/gold_standards.yaml`
  - **Acción:** Modificar
  - **Descripción:** Categorizar ejemplos para inyección selectiva según el especialista activo.

---

## Fase 3: Integridad de Memoria y Datos

### Objetivo
Eliminar el error `KeyError: 'buffer'` y estandarizar la comunicación entre capas.

### Justificación
La estabilidad de la memoria es el pilar de un "Soporte Vital".

### Cambios Previstos
- **Módulo/Archivo:** `src/memory/long_term_memory.py`
  - **Acción:** Modificar
  - **Descripción:** Implementar `MemorySummary` como Pydantic Model. El buffer siempre debe ser una lista.
- **Módulo/Archivo:** `src/memory/consolidation_worker.py`
  - **Acción:** Modificar
  - **Descripción:** Cambiar acceso a `data["buffer"]` por `.get("buffer", [])` y validaciones defensivas.

---

## Fase 4: Blindaje de Identidad (Post-Processing)

### Objetivo
Erradicar el "tío" y regionalismos accidentales mediante un filtro de seguridad.

### Justificación
Incluso con prompts perfectos, los LLMs pueden alucinar modismos. Un filtro final garantiza la coherencia.

### Cambios Previstos
- **Módulo/Archivo:** `src/core/lingua_guard.py`
  - **Acción:** Crear
  - **Descripción:** Filtro que escanea la respuesta final de la IA buscando palabras prohibidas y las sustituye por términos neutros.
- **Módulo/Archivo:** `src/api/services/event_processor.py`
  - **Acción:** Modificar
  - **Descripción:** Integrar el `LinguaGuard` antes de que el evento de respuesta sea publicado en el bus.

---

## Seguimiento de Tareas

- [ ] Implementar Motores Duales en `engine.py`.
- [ ] Refactorizar `prompt_builder.py` para aislamiento técnico.
- [ ] Aplicar fix de contrato Pydantic en `long_term_memory.py`.
- [ ] Crear el servicio `lingua_guard.py` e integrarlo en el pipeline.
- [ ] Ejecutar `make verify` y verificar logs en VM de Google Cloud.

---

## Notas y Riesgos
- **Riesgo de Cuota:** El modelo 120B de Groq puede tener límites de uso más bajos. Debemos monitorear los errores de `RateLimit`.
- **Latencia de Fallback:** Si Groq y Gemini fallan en cadena, el sistema debe devolver un "MAGI_ERROR_STANDBY" predefinido al usuario.
