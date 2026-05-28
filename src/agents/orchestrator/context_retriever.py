# src/agents/orchestrator/context_retriever.py
import json
import logging
import time

from src.core.dependencies import get_vector_memory_manager, redis_connection
from src.core.schemas.graph import GraphStateV2
from src.memory.knowledge_base import knowledge_base_manager
from src.memory.long_term_memory import long_term_memory

logger = logging.getLogger(__name__)

# Intents conversacionales básicos que no activan búsqueda semántica documental pesada
CASUAL_INTENTS = {"casual_greeting", "farewell", "acknowledgement"}


async def _load_evolution_note(chat_id: str) -> tuple[str | None, bool]:
    """
    Intenta cargar la nota evolutiva de Redis.
    Retorna (nota, cache_hit)
    """
    if redis_connection is None:
        return None, False

    try:
        # Clave específica de nota evolutiva v0.9.0
        evo_key = f"chat:evolution_note:{chat_id}"
        val = await redis_connection.get(evo_key)
        if val:
            if isinstance(val, bytes):
                val = val.decode("utf-8")
            try:
                data = json.loads(val)
                return data.get("summary"), True
            except Exception:
                return val, True

        # Fallback al summary clásico de largo plazo
        sum_key = f"chat:summary:{chat_id}"
        val = await redis_connection.get(sum_key)
        if val:
            if isinstance(val, bytes):
                val = val.decode("utf-8")
            try:
                data = json.loads(val)
                return data.get("summary"), True
            except Exception:
                return val, True
    except Exception as e:
        logger.warning(f"Error cargando nota evolutiva de Redis: {e}")

    return None, False


async def context_retriever_node(state: GraphStateV2) -> GraphStateV2:  # noqa: C901
    """
    Nodo de LangGraph dedicado a la recuperación RAG y la unificación de contexto.
    Calcula el snapshot RAG antes de invocar a los especialistas.
    """
    event = state.get("event")
    if not event:
        logger.warning("No event found in GraphStateV2 in context_retriever_node")
        state["rag_context"] = None
        return state

    chat_id = str(event.chat_id)
    user_message = str(event.content or "")
    payload = state.get("payload") or {}
    routing_meta = payload.get("routing_metadata", {})
    intent = routing_meta.get("intent", "unknown")

    # 1. Cargar Nota Evolutiva
    evolution_note, cache_hit = await _load_evolution_note(chat_id)
    if not evolution_note:
        # Fallback SQLite a través de long_term_memory
        memory_data = await long_term_memory.get_summary(chat_id)
        evolution_note = memory_data.get("summary", "Sin historial previo.")

    # 2. Condición: Intents Conversacionales
    if (
        intent in CASUAL_INTENTS
        or payload.get("processing_type") == "conversational_only"
    ):
        logger.info(
            f"[CONTEXT-RETRIEVER] Casual intent '{intent}' detected. Skipping semantical search."
        )
        state["rag_context"] = {
            "semantic_fragments": [],
            "graph_fragments": [],
            "evolution_note": evolution_note,
            "structured_facts": [],
            "total_tokens_estimated": 0,
            "retrieved_at": time.time(),
            "cache_hit": cache_hit,
        }
        return state

    # 3. Intents No Casuales: Recuperación Completa
    logger.info(f"[CONTEXT-RETRIEVER] Complete context retrieval for intent '{intent}'")

    semantic_fragments = []
    graph_fragments = []
    structured_facts = []

    try:
        manager = get_vector_memory_manager()
        # A. Búsqueda vectorial
        allowed_types = ["fact", "document"]

        # Consultar conocimiento global (TCC, etc) y del usuario
        global_results = await manager.retrieve_context(
            user_id="system",
            query=user_message,
            limit=3,
            namespace="global",
            context_type=allowed_types,
        )
        user_results = await manager.retrieve_context(
            user_id=chat_id,
            query=user_message,
            limit=2,
            namespace=f"user_{chat_id}",
            context_type=allowed_types,
        )

        raw_candidates = global_results + user_results

        # C. Reranker Semántico basado en API (Gemini) (Tarea 2.7)
        if raw_candidates:
            from src.memory.reranker import SemanticReranker

            reranker = SemanticReranker()
            # Ordenamos y filtramos a los Top-4 más relevantes combinados
            semantic_fragments = await reranker.rerank(
                user_message, raw_candidates, top_k=4
            )
        else:
            semantic_fragments = []

        # Graph-RAG Transversal: Expansión de Grafo (ADR-0033) (Tarea 3.4)
        # Los intents analíticos ejecutan búsquedas multi-salto
        analytical_intents = {"life_review", "pattern_analysis", "cross_domain_query"}
        if intent in analytical_intents and semantic_fragments:
            try:
                from src.memory.graph_search import expand_with_edges

                seed_ids = [item["id"] for item in semantic_fragments if "id" in item]
                graph_fragments = await expand_with_edges(
                    store=manager.store, seed_memory_ids=seed_ids, max_hops=2
                )
            except Exception as ge:
                logger.warning(f"Error expandiendo grafo en context_retriever: {ge}")

        # B. Cargar hechos estructurados filtrando por confianza >= 0.7
        try:
            raw_facts = await knowledge_base_manager.load_knowledge(chat_id)
            facts_list = []
            # Iterar secciones de la bóveda (entities, preferences, etc.)
            vault_sections = [
                "entities",
                "preferences",
                "medical",
                "relationships",
                "milestones",
            ]
            for section in vault_sections:
                items = raw_facts.get(section, [])
                if not isinstance(items, list):
                    continue
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    fact_key = item.get("key")
                    fact_value = item.get("value")
                    if not fact_key:
                        continue
                    confidence = float(item.get("confidence", 1.0))
                    if confidence >= 0.7:
                        facts_list.append({
                            "key": fact_key,
                            "value": str(fact_value) if fact_value else "",
                            "confidence": confidence,
                            "evidence": item.get("evidence"),
                        })
            # Incluir user_name si está presente
            if raw_facts.get("user_name"):
                facts_list.append({
                    "key": "user_name",
                    "value": str(raw_facts["user_name"]),
                    "confidence": 1.0,
                    "evidence": None,
                })
            structured_facts = facts_list
        except Exception as ke:
            logger.warning(f"Error al cargar structured knowledge para RAG: {ke}")

    except Exception as e:
        logger.error(f"Error en context_retriever_node: {e}", exc_info=True)

    # 4. Estimación de tokens y guardia (Límite 2000 tokens)
    # 1 token es aprox 4 caracteres.
    total_chars = sum(len(f.get("content", "")) for f in semantic_fragments)
    total_chars += sum(len(f.get("content", "")) for f in graph_fragments)
    total_chars += sum(len(f"{f['key']}: {f['value']}") for f in structured_facts)
    total_chars += len(evolution_note or "")

    total_tokens_estimated = total_chars // 4
    logger.debug(
        f"[CONTEXT-RETRIEVER] Estimated context tokens: {total_tokens_estimated}"
    )

    # Guardia de límite: Si supera 2000 tokens, truncar semantic_fragments primero
    if total_tokens_estimated > 2000 and len(semantic_fragments) > 2:
        semantic_fragments = semantic_fragments[:2]
        # Recalcular
        total_chars = sum(len(f.get("content", "")) for f in semantic_fragments)
        total_chars += sum(len(f.get("content", "")) for f in graph_fragments)
        total_chars += sum(len(f"{f['key']}: {f['value']}") for f in structured_facts)
        total_chars += len(evolution_note or "")
        total_tokens_estimated = total_chars // 4

    state["rag_context"] = {
        "semantic_fragments": semantic_fragments,
        "graph_fragments": graph_fragments,  # Será populado en la Fase 3
        "evolution_note": evolution_note,
        "structured_facts": structured_facts,
        "total_tokens_estimated": total_tokens_estimated,
        "retrieved_at": time.time(),
        "cache_hit": cache_hit,
    }

    return state
