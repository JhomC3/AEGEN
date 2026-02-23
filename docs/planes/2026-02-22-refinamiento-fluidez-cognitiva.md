# PLAN: Refinamiento de Fluidez Cognitiva (Late Context Injection)

> **Instrucciones para Agentes:**
> - Para **crear** o modificar este plan: Usar la skill `writing-plans`.
> - Para **ejecutar** este plan: Usar la skill `executing-plans` para proceder tarea por tarea con verificaciones intermedias.

- **Estado:** Propuesto
- **Fecha:** 2026-02-22
- **Razón de Creación:** Inestabilidad de tono en historiales largos (Role Clash). El asistente adopta tonos robóticos y terapéuticos clichés cuando el historial es extenso, perdiendo la identidad de "amigo cercano" a pesar de las directrices base.
- **Objetivo General:** Implementar inyección tardía de contexto (Late Context Injection) para priorizar las instrucciones de tono, relajar el enrutamiento terapéutico estricto y sustituir directrices abstractas por restricciones negativas ejecutables.

---

## Análisis de Impacto

### Dependencias afectadas
- `src/personality/skills/tcc_overlay.md`: Cambio de paradigma (de instrucciones positivas abstractas a restricciones negativas concretas).
- `src/prompts/cbt_therapeutic_response.txt`: Actualización alineada con el overlay.
- `src/agents/orchestrator/routing/therapeutic_session.py`: Relajación de la retención de sesión.
- `src/agents/specialists/cbt/cbt_tool.py`: Implementación de Late Context Injection.
- `src/agents/specialists/chat/chat_tool.py`: Implementación de Late Context Injection.

### Cobertura de tests existente
- Validar `tests/integration/test_conversational_flow.py` para asegurar que el enrutamiento y la generación no se rompen con la inyección tardía de prompts.

---

## Fase 1: Reingeniería Anti-Robótica (Negative Constraints)

### Objetivo
Eliminar instrucciones que el LLM malinterpreta como "habla como terapeuta de manual".

### Cambios Previstos
- **Módulo/Archivo:** `src/personality/skills/tcc_overlay.md`
  - **Acción:** Modificar
  - **Descripción:** Reemplazar "Valida el cansancio o frustración..." por "PROHIBIDO nombrar la emoción del usuario ("entiendo que te sientas triste"). En su lugar, demuestra que lo entiendes proponiendo una solución práctica o cambiando el enfoque".
- **Módulo/Archivo:** `src/prompts/cbt_therapeutic_response.txt`
  - **Acción:** Modificar
  - **Descripción:** Eliminar cualquier mención a "Validación implícita". Insertar la regla de oro: "Nunca uses la estructura 'Entiendo que te sientas X'".

---

## Fase 2: Relajación del Router Terapéutico

### Objetivo
Permitir que el usuario "rompa" la sesión terapéutica si se siente abrumado o si el asistente se equivoca de tono.

### Cambios Previstos
- **Módulo/Archivo:** `src/agents/orchestrator/routing/therapeutic_session.py`
  - **Acción:** Modificar
  - **Descripción:** En la función `should_maintain_therapeutic_session`, añadir una excepción. Si el intent es `CONFUSION` o `RESISTANCE` (o si la confianza del intent actual es baja y sugiere enojo), devolver `False` para permitir que el sistema escape hacia el `chat_specialist` general y "pida disculpas como amigo" en lugar de forzar la terapia.

---

## Fase 3: Late Context Injection (El Martillazo)

### Objetivo
Vencer el efecto "Lost in the Middle" de los LLMs.

### Cambios Previstos
- **Módulo/Archivo:** `src/agents/specialists/cbt/cbt_tool.py` y `src/agents/specialists/chat/chat_tool.py`
  - **Acción:** Modificar
  - **Descripción:** Ajustar el `ChatPromptTemplate`. Después del `MessagesPlaceholder` (que inyecta el historial), agregar un último mensaje `SystemMessage` con las reglas críticas de tono: "RECUERDA: Eres un amigo cercano, no un robot. Sé breve. No uses clichés terapéuticos. Tuteo neutro." Esto fuerza la atención del LLM justo antes de responder.

---

## Seguimiento de Tareas

- [ ] Modificar `tcc_overlay.md` y `cbt_therapeutic_response.txt` (Negative Constraints).
- [ ] Ajustar lógica en `therapeutic_session.py`.
- [ ] Implementar Late Context Injection en `cbt_tool.py`.
- [ ] Implementar Late Context Injection en `chat_tool.py`.
- [ ] Ejecutar validación `make verify`.
