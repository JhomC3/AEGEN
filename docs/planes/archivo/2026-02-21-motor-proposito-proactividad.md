# PLAN: Motor de Propósito y Proactividad Asíncrona

> **Instrucciones para Agentes:**
> - Para **crear** o modificar este plan: Usar la skill `writing-plans`.
> - Para **ejecutar** este plan: Usar la skill `executing-plans` para proceder tarea por tarea con verificaciones intermedias.
> - **Criterio de calidad:** Evaluar trade-offs de cada cambio respecto a: puntos únicos de fallo, degradación suave, y acoplamiento entre módulos. Aceptar complejidad solo cuando el ROI lo justifique (Principio Core #2).

- **Estado:** Completado
- **Fecha:** 2026-02-21
- **Razón de Creación:** Nueva Funcionalidad (Bloque 2 y 3 del Plan Estratégico)
- **ADR Relacionado:** ADR-0026, ADR-0027
- **Objetivo General:** Implementar el seguimiento de estado del usuario (Metas e Hitos) y dotar al sistema de una arquitectura *Outbox* que permita el envío asíncrono y proactivo de mensajes.

---

## Resumen Ejecutivo

Para que AEGEN actúe como un "Soporte Vital", necesita memoria direccional y capacidad de iniciar conversaciones. Este plan introduce cambios estructurales en la base de datos para almacenar `user_goals` y `user_milestones`. Además, crea el motor proactivo mediante un patrón de "Bandeja de Salida Diferida" (Outbox) con un polling periódico asociado al adaptador de Telegram. Por último, separamos la lógica experta cruda de la respuesta conversacional.

---

## Análisis de Impacto

### Dependencias afectadas
- [ ] Ejecutar `grep -r 'from <modulo_modificado>' src/` y listar todos los módulos que importan desde archivos modificados
  - *Archivos a modificar:* `src/memory/schema.sql`, `src/memory/migration.py`, `src/api/adapters/telegram_adapter.py`, `src/api/routers/webhooks.py`, `src/personality/prompt_builder.py`.
  - *Consumidores:* Gran parte del core.

### Cobertura de tests existente
- [ ] Ejecutar `grep -r '<funcion_o_clase>' tests/` para identificar qué tests cubren el código afectado
  - *Tests a verificar:* `tests/unit/memory/test_sqlite_store.py`, `tests/integration/test_telegram_webhook.py`.
- [ ] Si cobertura es cero: crear tests ANTES de modificar el código. Se DEBEN crear tests unitarios para las nuevas tablas y la lógica del Outbox.

### Verificación del pipeline
- [ ] Al alterar el ciclo principal de `telegram_adapter.py` y el esquema base, cualquier error aquí puede romper todo el sistema de respuesta. Se requiere un testing exhaustivo e incremental (Micro-gates rigurosos).

---

## Fase 1: Motor de Seguimiento Estructurado (State Management)

### Objetivo
Aplicar el ADR-0026. Permitir guardar metas a largo plazo y registrar eventos vitales diarios (hitos).

### Cambios Previstos
- **Módulo/Archivo:** `src/memory/schema.sql` y `src/memory/migration.py`
  - **Acción:** Modificar
  - **Descripción:** Añadir tablas `user_goals` y `user_milestones`. Crear el script de migración asíncrono e idempotente correspondiente.
- **Módulo/Archivo:** `src/memory/repositories/`
  - **Acción:** Crear/Modificar
  - **Descripción:** Repositorio para escritura/lectura fácil de estas nuevas tablas.
- **Módulo/Archivo:** `src/personality/prompt_builder.py`
  - **Acción:** Modificar
  - **Descripción:** Extraer e inyectar los últimos 3 hitos activos no resueltos en el contexto de runtime de MAGI.

## Fase 2: Extracción en Background de Hitos

### Objetivo
No obligar al usuario a decir "Añade esto a mis hitos", sino que el sistema los detecte naturalmente de la conversación.

### Cambios Previstos
- **Módulo/Archivo:** `src/memory/services/consolidation_worker.py` (o creación de uno nuevo)
  - **Acción:** Modificar/Crear
  - **Descripción:** Dentro del proceso diferido de consolidación de memoria, añadir un paso de extracción con Pydantic/Instructor para detectar si se ha cumplido algún hito relevante, guardándolo en la BD.

## Fase 3: Bandeja de Salida (Outbox Pattern) y Cronógrafo Proactivo

### Objetivo
Aplicar el ADR-0027. Permitir al sistema agendar y despachar mensajes al futuro.

### Cambios Previstos
- **Módulo/Archivo:** `src/memory/schema.sql`
  - **Acción:** Modificar
  - **Descripción:** Crear tabla `outbox_messages` con scheduling.
- **Módulo/Archivo:** `src/core/messaging/outbox.py`
  - **Acción:** Crear
  - **Descripción:** Servicio para insertar mensajes diferidos o cancelarlos (debounce).
- **Módulo/Archivo:** `src/api/adapters/telegram_adapter.py` y/o `lifespan` de FastAPI
  - **Acción:** Modificar
  - **Descripción:** Añadir una tarea asíncrona en bucle (`asyncio.sleep(60)`) que revise la BD cada minuto y despache los mensajes a través del bot API de Telegram a su hora programada.

## Fase 4: Inyección Suave de Intención (Soft Intent Injection)

### Objetivo
Asegurar que si el usuario habla primero, los mensajes proactivos pendientes no se borren sin más (Hard Cancel), sino que se inyecten como contexto en la nueva conversación.

### Cambios Previstos
- **Módulo/Archivo:** `src/core/messaging/outbox.py`
  - **Acción:** Modificar
  - **Descripción:** Cambiar `cancel_pending` por un método `get_and_clear_pending_intents` que devuelva las intenciones programadas y las elimine del Outbox.
- **Módulo/Archivo:** `src/api/services/event_processor.py`
  - **Acción:** Modificar
  - **Descripción:** Al iniciar el procesamiento de un evento de usuario, consultar los `pending_intents` y agregarlos al `payload`.
- **Módulo/Archivo:** `src/personality/prompt_builder.py`
  - **Acción:** Modificar
  - **Descripción:** Inyectar una instrucción en el prompt indicando que había una intención programada y que el LLM debe decidir si es prudente traerla a colación de forma natural.

---

## Seguimiento de Tareas

- [ ] Aprobar/Revisar ADR-0026 y ADR-0027.
- [ ] Fase 1: Alterar schemas y crear repositorios de acceso.
- [ ] Fase 1: Escribir tests para el nuevo repositorio de State Management.
- [ ] Fase 2: Implementar la extracción estructurada por LLM en background y sus tests.
- [ ] Fase 3: Crear schema del outbox y servicio de encolado.
- [ ] Fase 3: Implementar loop asíncrono en Telegram Adapter.
- [ ] Fase 3: Probar el flujo completo: agendar mensaje a T+1 minuto y verificar recepción en Telegram.
- [ ] Ejecutar la suite completa de `make verify` y `pytest tests/integration/`.

---

## Desviaciones

> Esta sección se llena **durante la ejecución**, no durante la planificación.

| Fecha | Desviación | Razón | Impacto |
|---|---|---|---|
| | | | |

---

## Notas y Riesgos
- **Concurrencia de Outbox:** Si hay varios workers levantados (ej. múltiples instancias de FastAPI), un mensaje del Outbox podría enviarse doblemente. Debemos usar una cláusula SQL `UPDATE ... RETURNING` o `SELECT FOR UPDATE` (limitado en SQLite pero manejable con transacciones exclusivas de escritura `BEGIN EXCLUSIVE`) para asegurar que solo 1 worker despacha el mensaje.
