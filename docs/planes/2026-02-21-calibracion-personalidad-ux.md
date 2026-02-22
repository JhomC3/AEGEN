# PLAN: Calibración de Personalidad e In-Context Learning (Core UX)

> **Instrucciones para Agentes:**
> - Para **crear** o modificar este plan: Usar la skill `writing-plans`.
> - Para **ejecutar** este plan: Usar la skill `executing-plans` para proceder tarea por tarea con verificaciones intermedias.
> - **Criterio de calidad:** Evaluar trade-offs de cada cambio respecto a: puntos únicos de fallo, degradación suave, y acoplamiento entre módulos. Aceptar complejidad solo cuando el ROI lo justifique (Principio Core #2).

- **Estado:** Propuesto
- **Fecha:** 2026-02-21
- **Razón de Creación:** Refactorización (Mejora Crítica de Experiencia de Usuario)
- **ADR Relacionado:** N/A (Solo altera prompts y configuración interna de personalidad, sin modificar schemas o interfaces base)
- **Objetivo General:** Eliminar el comportamiento robótico, interrogativo y de "Tough Love" forzado del asistente, sustituyendo reglas negativas por *Few-Shot Prompting* (Gold Standards) para un soporte conversacional natural.

---

## Resumen Ejecutivo

Actualmente, las respuestas de MAGI en TCC y chat general resultan incómodas por tres razones: (1) Uso de un "voseo" erróneo inferido por el LLM, (2) Instrucciones agresivas de reestructuración que causan que el bot asuma premisas ("¿Qué pruebas tienes...?") y (3) falta de un hilo conductor (hace múltiples preguntas o intentos de cerrar el problema en cada mensaje). Este plan limpia los `_overlay.md`, el `prompt_builder.py` y los prompts de TCC, e introduce un archivo de *Gold Standards* para enseñar por imitación en lugar de prohibición.

---

## Análisis de Impacto

### Dependencias afectadas
- [ ] Ejecutar `grep -r 'from <modulo_modificado>' src/` y listar todos los módulos que importan desde archivos modificados
  - *Archivos a modificar:* `src/personality/base/SOUL.md`, `src/personality/skills/tcc_overlay.md`, `src/personality/prompt_builder.py`, `src/prompts/cbt_therapeutic_response.txt`, `src/agents/specialists/cbt/cbt_tool.py`.
  - *Consumidores:* `personality_manager.py`, `master_orchestrator.py`, `cbt_tool.py`.
- [ ] Identificar schemas Pydantic que son inputs/outputs de funciones modificadas: Ninguno se ve afectado.
- [ ] Verificar si el cambio afecta alguna interfaz en `src/core/interfaces/`: Ninguna.

### Cobertura de tests existente
- [ ] Ejecutar `grep -r '<funcion_o_clase>' tests/` para identificar qué tests cubren el código afectado
  - *Tests a verificar:* `tests/unit/personality/test_prompt_builder.py`, `tests/unit/personality/test_style_analyzer.py`.
- [ ] Si cobertura es cero: crear tests ANTES de modificar el código.

### Verificación del pipeline
- [ ] Si el cambio toca `src/api/`, `src/agents/`, o `src/tools/telegram/`: trazar el flujo completo y confirmar que sigue intacto (Solo afectaremos los strings de los templates y el builder).

---

## Fase 1: Purga de Hardcodes y Voseo

### Objetivo
Asegurar que el asistente utilice un tono neutro-cálido garantizado (tuteo), eliminando las directivas agresivas de coaching.

### Cambios Previstos
- **Módulo/Archivo:** `src/personality/base/SOUL.md`
  - **Acción:** Modificar
  - **Descripción:** Agregar una directiva explícita e inmutable que prohíba estrictamente el voseo rioplatense (vos, tenés, podés) a menos que se haya seteado un `preferred_dialect` de forma explícita.
- **Módulo/Archivo:** `src/personality/skills/tcc_overlay.md`
  - **Acción:** Modificar
  - **Descripción:** Eliminar la sección de "Tough Love" y la directiva de "¿Qué pruebas tienes de que eso sea cierto?". Cambiar el enfoque hacia "Firmeza Empática y Escucha Activa", evitando interrogar.

## Fase 2: Conversational Pacing (El Hilo Conductor)

### Objetivo
Evitar que el agente parezca un manual intentando resolver toda la vida del usuario en un solo mensaje.

### Cambios Previstos
- **Módulo/Archivo:** `src/prompts/cbt_therapeutic_response.txt`
  - **Acción:** Modificar
  - **Descripción:** Reducir las instrucciones a "Solo dar un paso a la vez". Prohibir expresamente incluir más de una pregunta en una misma respuesta y fomentar respuestas concisas.
- **Módulo/Archivo:** `src/agents/orchestrator/routing/enhanced_router.py` (Sección de Pacing/Instrucciones)
  - **Acción:** Modificar
  - **Descripción:** Reforzar las instrucciones pasadas al LLM para que respete el ritmo de la conversación (Pacing).

## Fase 3: Implementación de Gold Standards (Few-Shot Dinámico)

### Objetivo
Sustituir las "reglas de prohibición" por "ejemplos de perfección".

### Cambios Previstos
- **Módulo/Archivo:** `src/personality/base/gold_standards.yaml` (o `.json`)
  - **Acción:** Crear
  - **Descripción:** Un archivo conteniendo 3-4 ejemplos *Few-Shot* de cómo debe responder a situaciones de desahogo y apatía de manera natural y de soporte.
- **Módulo/Archivo:** `src/personality/prompt_builder.py`
  - **Acción:** Modificar
  - **Descripción:** Agregar la lógica para cargar el archivo `gold_standards.yaml` e inyectar un par de ejemplos en la "Capa Espejo" (Capa 3) o "Capa Skill" del Soul Stack, mostrando explícitamente el "Input del Usuario" y el "Output Ideal".

---

## Seguimiento de Tareas

- [ ] Modificar `SOUL.md` para purgar voseo.
- [ ] Limpiar `tcc_overlay.md` de reglas agresivas.
- [ ] Crear el script de purgado temporal para limpiar la preferencia de acento errónea en la base de datos (perfil SQLite).
- [ ] Actualizar los prompts de `cbt_therapeutic_response.txt` para limitar a 1 pregunta máxima.
- [ ] Crear el archivo `gold_standards.yaml` con ejemplos positivos de la nueva visión.
- [ ] Modificar `prompt_builder.py` para inyectar estos *Gold Standards*.
- [ ] Ejecutar `make verify` y correr tests de la capa de personalidad.

---

## Desviaciones

> Esta sección se llena **durante la ejecución**, no durante la planificación.

| Fecha | Desviación | Razón | Impacto |
|---|---|---|---|
| | | | |

---

## Notas y Riesgos

- El uso de "Few-Shot" incrementa ligeramente el consumo de tokens en cada petición. Dado que usamos un modelo moderno, el impacto en costo/latencia debería ser despreciable comparado con la ganancia en UX.
