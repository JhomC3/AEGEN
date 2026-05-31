# ADR-0037 - Bucle de Aprendizaje Continuo: Nudge de Memoria, Curador y Compresión de Contexto

- **Fecha:** 2026-05-29
- **Estado:** Aceptado
- **Autor:** MAGI AI
- **ADR Relacionado:** ADR-0026 (Agentic Skills Hub), ADR-0032 (Ingesta Atómica), ADR-0030 (Time Decay)
- **Inspiración:** Hermes-agent (https://github.com/NousResearch/hermes-agent)

## Contexto

El sistema actual almacena conversaciones y extrae facts en background. Sin embargo, el proceso de aprendizaje es **pasivo**: solo ocurre cuando el `ConsolidationWorker` se dispara (cada 10 mensajes o 30 minutos). Entre ciclos de consolidación, el sistema no aprende nada de la conversación en curso.

Hermes-agent introduce tres patrones complementarios que producen un bucle de aprendizaje activo:

1. **Nudge post-turno de memoria:** Tras cada N turnos, evaluar si hay hechos nuevos dignos de guardar, sin esperar a la consolidación.
2. **Curador de skills:** Worker en background que gestiona el ciclo de vida de skills (stale → archive).
3. **Compresión de contexto por LLM:** Cuando la conversación se acerca al límite de tokens, resumir el historial medio con un modelo auxiliar en lugar de truncar ciegamente.

Adicionalmente, la **búsqueda sobre sesiones previas** (session search) es una capacidad ausente: MAGI no puede consultar "¿qué hablamos sobre X la semana pasada?" contra su propio historial.

## Decisión

### 1. Nudge de Memoria Post-Turno

Después de cada respuesta enviada al usuario, el sistema evalúa si debe extraer y persistir hechos de los últimos N turnos (N=3 por defecto). Esto complementa el `ConsolidationWorker` sin reemplazarlo.

**Trigger:** El nodo `chain_router` o el middleware de respuesta lanza un evento `conversation.turn_completed` en el bus. Un worker ligero escucha este evento.

**Lógica del nudge:**

```python
async def memory_nudge_worker(event: CanonicalEventV1) -> None:
    chat_id = event.chat_id
    turn_count = await redis.incr(f"chat:turn_count:{chat_id}")

    if turn_count % NUDGE_EVERY_N_TURNS != 0:
        return  # No es turno de nudge

    recent_messages = await redis.lrange(f"chat:buffer:{chat_id}", 0, -1)
    if not recent_messages:
        return

    # Extractor ligero: solo busca preferencias y hechos concretos
    # Usa get_fast_llm() para minimizar latencia
    new_facts = await _extract_lightweight_facts(recent_messages)
    for fact in new_facts:
        await ingestion_pipeline.save_knowledge(chat_id=chat_id, fact=fact)
```

El nudge usa `get_fast_llm()` (Groq), no el modelo analítico. El prompt es minimalista: solo extrae preferencias explícitas ("prefiero X", "no me gusta Y") y hechos concretos verificables. No genera resúmenes ni análisis — eso lo hace el `ConsolidationWorker`.

**Desduplicación:** Antes de guardar, verificar si existe un fact similar con `keyword_search` (FTS5). Si la similitud es >0.9, actualizar el fact existente en lugar de crear uno duplicado.

### 2. Session Search Tool

Implementar `search_conversation_history` como LangChain tool accesible desde los especialistas.

**Requisito previo:** El método `search_conversations()` **no existe** en `src/memory/keyword_search.py`. La clase `KeywordSearch` solo tiene `search()` con parámetros limitados (`query_text`, `limit`, `chat_id`, `namespace`, `source_skill`). Se requiere **extender** `KeywordSearch` con un nuevo método que soporte filtrado temporal y por tipo:

```python
# NUEVO método en src/memory/keyword_search.py
async def search_conversations(
    self,
    query_text: str,
    namespace: str,
    type_filter: str | None = None,
    days_back: int = 30,
    limit: int = 5,
) -> list[dict]:
    """
    Búsqueda FTS5 en conversaciones con filtrado temporal.

    Args:
        query_text: Términos de búsqueda.
        namespace: Namespace del usuario (ej. "user_123").
        type_filter: Filtrar por tipo de memoria (ej. "conversation").
        days_back: Solo resultados de los últimos N días.
        limit: Máximo de resultados.
    """
    # Implementación: extender el query FTS5 con JOIN a memories
    # y filtro WHERE created_at >= datetime('now', '-{days_back} days')
```

**Tool de LangChain:**

```python
@tool
async def search_conversation_history(
    query: str,
    chat_id: str,
    days_back: int = 30,
) -> str:
    """
    Busca en el historial de conversaciones del usuario.
    Usar cuando el usuario pregunta por algo que se dijo en una sesión anterior.
    Ejemplo: '¿qué dijimos sobre mi dieta la semana pasada?'
    """
    results = await keyword_search.search_conversations(
        query_text=query,
        namespace=f"user_{chat_id}",
        type_filter="conversation",
        days_back=days_back,
        limit=5,
    )
    return format_conversation_results(results)
```

Usa el índice FTS5 ya existente en `keyword_search.py` — sin nueva infraestructura de búsqueda. Se registra en `tools.py` del skill `chat` y `tcc`.

### 3. Curador Automático de Skills

Un worker programado (ejecución semanal, vía el `scheduler` existente en `src/agents/scheduler/`) que gestiona el ciclo de vida de skills:

**Estados de skill:**
- `active` → Se carga normalmente al arrancar.
- `stale` → No se ha activado en >30 días. Se carga pero aparece marcada en logs.
- `archived` → Movida a `src/personality/skills/.archive/`. No se carga.

**Métricas de uso:** El `skill_loader.py` registra en Redis el último momento de activación de cada skill: `HSET skill:last_used {skill_id} {timestamp}`.

**Lógica del curador:**

```python
async def run_skill_curator(dry_run: bool = False) -> dict:
    skills = await skill_loader.list_all_skills()
    report = {"stale": [], "archived": [], "consolidated": []}

    for skill in skills:
        last_used = await redis.hget("skill:last_used", skill.id)
        if not last_used:
            continue  # Nunca usada — no penalizar skills nuevas

        days_inactive = (datetime.utcnow() - last_used).days

        if days_inactive > 90 and not dry_run:
            await _archive_skill(skill)
            report["archived"].append(skill.id)
        elif days_inactive > 30:
            report["stale"].append(skill.id)

    return report
```

El modo `--dry-run` solo genera el reporte sin mover archivos. El administrador recibe el reporte por Telegram (via `AdminNotificator`).

### 4. Compresión de Contexto por LLM

Cuando el historial de conversación en Redis supera el 80% del límite de tokens del modelo, se activa la compresión:

**Estrategia:** Preservar los primeros 3 mensajes (contexto inicial) y los últimos 5 (contexto reciente). Resumir el bloque medio con `get_fast_llm()`.

```python
async def compress_context_if_needed(
    messages: list[dict],
    token_limit: int,
    preserve_start: int = 3,
    preserve_end: int = 5,
) -> list[dict]:
    estimated_tokens = sum(len(m["content"]) // 4 for m in messages)

    if estimated_tokens < token_limit * 0.8:
        return messages  # No compresión necesaria

    start = messages[:preserve_start]
    end = messages[-preserve_end:]
    middle = messages[preserve_start:-preserve_end]

    if not middle:
        return messages

    summary = await _summarize_messages(middle)  # Gemini Flash
    summary_message = {
        "role": "system",
        "content": f"[Resumen de conversación anterior] {summary}",
    }
    return start + [summary_message] + end
```

La compresión es transparente para el LLM principal: recibe los mismos roles/content, con el bloque medio comprimido en un mensaje de sistema.

### 5. Feedback de Aristas del Grafo vía ConsolidationWorker

El `ConsolidationWorker` ya evalúa la conversación para generar resúmenes y detectar evolución. Se añade un paso de **evaluación de utilidad de fragmentos**: el LLM de consolidación (Gemini Flash, `get_rag_llm()`) analiza qué fragmentos del grafo —inyectados en el contexto vía Graph-RAG— fueron realmente pertinentes a la dirección de la conversación.

**Rechazo explícito de cosine similarity:** Evaluar utilidad con métricas vectoriales (cosine similarity entre respuesta y fragmento) produce falsos positivos masivos — la respuesta conversacional contiene saludos, preguntas, empatía y transiciones que contaminan la similaridad con hechos específicos. Solo el LLM puede determinar si un fragmento fue *semánticamente pertinente* al razonamiento.

**Algoritmo:**

```python
# En consolidation_worker.py, tras _generate_transversal_edges():
async def _adjust_edge_weights_from_feedback(
    store, chat_id, conversation_history, injected_graph_fragments
) -> None:
    """
    El LLM evalúa qué fragmentos del grafo inyectados en el contexto
    fueron pertinentes. Los pesos de las aristas asociadas se refuerzan
    (+0.05) o se atenúan (−0.03).
    """
    if not injected_graph_fragments:
        return

    prompt = FEEDBACK_PROMPT.format(
        conversation=conversation_history[-20:],  # Últimos 20 mensajes
        fragments=format_fragments_with_edge_ids(injected_graph_fragments),
    )

    response = await get_rag_llm().ainvoke(prompt)
    useful_ids = parse_useful_ids(response)  # Extraer lista de IDs del JSON

    for frag in injected_graph_fragments:
        edge_id = frag.get("edge_id")
        if not edge_id:
            continue
        if frag["id"] in useful_ids:
            await _update_edge_weight(store, edge_id, delta=+0.05)
        else:
            await _update_edge_weight(store, edge_id, delta=-0.03)

    logger.info(
        f"[FEEDBACK] chat={chat_id}: {len(useful_ids)}/{len(injected_graph_fragments)} fragmentos útiles"
    )
```

**Efecto neto:**
- Aristas que producen insights que MAGI usa → suben de peso → aparecen más en futuras expansiones.
- Aristas que generan ruido → bajan de peso → eventualmente caen por debajo del umbral (0.3) y dejan de expandirse.
- Sin intervención humana. Sin batch jobs. En vivo, en cada ciclo de consolidación.
- Cero latencia para el usuario (ejecutado 100% en background).

**Nota:** Esta sección complementa la sección 1c del ADR-0034 (Graph-RAG Data-Driven), que define la arquitectura y el trigger. Esta sección define la implementación concreta del worker.

## Consecuencias

### Positivas
- **Aprendizaje continuo:** El sistema captura preferencias y hechos entre ciclos de consolidación. Con nudge cada 3 turnos, la latencia máxima de persistencia pasa de ~10 mensajes a ~3.
- **Grafo vivo:** El ConsolidationWorker evalúa qué conexiones entre dominios fueron útiles y ajusta los pesos de `memory_edges` en consecuencia. El grafo mejora con cada ciclo, sin intervención humana.
- **Sesiones largas sin truncamiento:** La compresión LLM preserva coherencia narrativa en sesiones de terapia de 60+ minutos.
- **Higiene de skills:** El curador previene la acumulación de skills obsoletas que aumentan el tiempo de arranque y consumen tokens de prompt.
- **Memoria episódica:** La session search tool permite a MAGI recuperar detalles específicos de conversaciones pasadas que el RAG vectorial suele perder (episodios concretos vs. semántica general).

### Negativas / Riesgos
- **Doble extracción:** El nudge y el `ConsolidationWorker` pueden extraer el mismo hecho. La desduplicación FTS5 mitiga esto, pero añade una query extra por fact nuevo. Costo: ~1-2ms por fact.
- **Latencia del nudge:** El nudge se ejecuta en background (no bloquea la respuesta al usuario). Sin embargo, si el bus de eventos está saturado, puede retrasarse varios minutos. Aceptable para el caso de uso.
- **Skills sin métricas de uso:** Skills que se cargan en el prompt pero no generan tool calls no se registran como "usadas". El curador podría archivar skills activas pero que operan solo vía prompt. Mitigación: registrar la carga de skill en el prompt como "uso", aunque sea implícito.
- **Compresión irreversible:** El resumen del bloque medio es lossy. Detalles específicos del historial comprimido pueden perderse. El campo `preserve_start + preserve_end` debe ajustarse según el tipo de sesión (terapia: más contexto preservado; trading: más compresión tolerada).
- **Feedback inicial ruidoso:** En usuarios nuevos con pocas aristas (<3 ciclos de consolidación), el LLM del ConsolidationWorker no tiene suficiente contexto para evaluar utilidad con precisión. Las aristas mantienen sus pesos iniciales hasta acumular suficiente historial.

### Decisiones descartadas

**Cosine similarity para feedback de aristas:** Se evaluó usar similitud de coseno entre la respuesta del LLM y los fragmentos expandidos para determinar utilidad. **Descartado** porque la respuesta conversacional contiene saludos, preguntas, empatía y transiciones que contaminan la similaridad con hechos específicos, produciendo falsos positivos masivos. El LLM en el ConsolidationWorker produce una evaluación semántica de pertinencia significativamente más precisa.
