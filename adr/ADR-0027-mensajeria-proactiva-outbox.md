# ADR-0027 - Arquitectura de Mensajería Proactiva y Bandeja de Salida (Outbox Pattern)

- **Fecha:** 2026-02-21
- **Estado:** Propuesto

## Contexto

El sistema AEGEN tiene una arquitectura estrictamente reactiva. El flujo de datos principal inicia únicamente cuando el webhook/long-polling de Telegram recibe un mensaje del usuario. El procesamiento concluye enviando una respuesta síncrona/asíncrona a la misma petición.
Para funcionar como un "Soporte Vital" y un agente integral, el sistema debe ser capaz de *iniciar* conversaciones. Por ejemplo, preguntar "¿Cómo te fue en el gimnasio?" a las 8:00 PM después de que el usuario haya indicado por la mañana que se sentía apático al respecto. No hay mecanismo actual para "despertar" al agente o enviarle un cron-job sin que el usuario interactúe primero.

## Decisión

1. **Implementar el Patrón Transactional Outbox:**
   - Crear una nueva tabla en SQLite (`outbox_messages` o `proactive_queue`) que almacene mensajes programados.
   - Campos clave: `id`, `chat_id`, `intent` (razón del mensaje), `scheduled_for` (timestamp de envío), `status` (pending, sent, cancelled).
   - Los agentes (como MAGI o el Extractor de Hitos) podrán emitir un "comando de programación" que insertará un registro en esta tabla para un envío futuro (diferido).

2. **Cronógrafo en el Adaptador de Telegram:**
   - Modificar el ciclo de long-polling o crear una tarea asíncrona (`asyncio.create_task`) que evalúe periódicamente (ej. cada minuto) la tabla `outbox_messages` en busca de mensajes cuyo `scheduled_for` sea menor o igual al tiempo actual.
   - Al cumplirse el tiempo, el sistema enviará un evento interno para despachar el mensaje al usuario a través del bot de Telegram.

3. **Lógica de Cancelación y Debounce:**
   - Si el usuario habla con el asistente *antes* de que se envíe el mensaje proactivo, el sistema deberá evaluar si el mensaje proactivo sigue siendo relevante o si debe cancelarse (actualizando el estado a `cancelled`) para evitar interrupciones antinaturales.

## Consecuencias

### Positivas
- AEGEN obtiene la verdadera agencia ("Proactividad"), pudiendo iniciar la conversación de manera autónoma.
- El patrón Outbox es tolerante a fallos: si la app se reinicia, los mensajes programados no se pierden ya que residen en la base de datos persistente.
- El agente puede ejecutar un "Seguimiento Terapéutico" realista, simulando una verdadera relación humana.

### Negativas / Riesgos
- **Riesgo de Spam:** Si la lógica de scheduling entra en bucle, el agente podría saturar al usuario de mensajes. Se requerirá un *rate limiting* duro a nivel de base de datos (ej. "No enviar más de 2 mensajes proactivos por día").
- **Colisiones de Contexto:** Si el bot envía un mensaje programado exactamente cuando el usuario estaba escribiendo sobre otro tema, la UX puede sentirse extraña.
- Aumento en la complejidad del ciclo de vida (Lifespan) de FastAPI, al requerir workers periódicos.
