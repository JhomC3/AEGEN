# src/agents/orchestrator/context_retriever.py
import json
import logging
import re
import time
import unicodedata
from datetime import UTC, datetime
from typing import Any

from src.core.dependencies import get_vector_memory_manager, redis_connection
from src.core.schemas.graph import GraphStateV2
from src.memory.knowledge_base import knowledge_base_manager
from src.memory.long_term_memory import long_term_memory

logger = logging.getLogger(__name__)


def _format_fact_age(created_at: str) -> str:
    """Formatea la antiguedad de un hecho en lenguaje natural."""
    try:
        ts = datetime.fromisoformat(created_at)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        delta = datetime.now(UTC) - ts
    except Exception:
        return ""

    if delta.days == 0:
        return "hoy"
    if delta.days <= 7:
        return f"hace {delta.days} dia{'s' if delta.days > 1 else ''}"
    if delta.days <= 30:
        weeks = delta.days // 7
        return f"hace {weeks} semana{'s' if weeks > 1 else ''}"
    if delta.days <= 365:
        months = delta.days // 30
        return f"hace {months} mes{'es' if months > 1 else ''}"
    years = delta.days // 365
    return f"hace {years} ano{'s' if years > 1 else ''}"


_CASUAL_PATTERN = re.compile(
    r"^\s*(hola|hey|buenas?\s*(tardes|dias|noches)?|ey|hi|hello|"
    r"ok|okey|vale|gracias|de nada|bye|hasta\s*(luego|pronto)?|"
    r"adi[oó]s|chao|entendido|claro|perfecto|"
    r"👋|🙋|👍|✅)\s*[!.?]*\s*$",
    re.IGNORECASE | re.UNICODE,
)


def _is_casual_message(text: str) -> bool:
    """Detecta mensajes triviales que no requieren búsqueda semántica."""
    normalized = unicodedata.normalize("NFC", text)
    return bool(_CASUAL_PATTERN.match(normalized))


async def _check_edges_exist(  # noqa: S608
    store: Any, memory_ids: list[int]
) -> bool:
    """
    Verifica si existe al menos una arista en memory_edges para los IDs dados.
    Verifica tanto origen_id como destino_id: las aristas son direccionales
    pero nos interesa saber si el fragmento participa en CUALQUIER relacion.
    Costo: <5ms si no hay aristas (caso tipico en sesiones nuevas).
    Usa parametros parametrizados (?); el f-string solo genera placeholders.
    """
    if not memory_ids:
        return False
    placeholders = ",".join("?" * len(memory_ids))
    query = (  # noqa: S608
        "SELECT 1 FROM memory_edges "
        f"WHERE origen_id IN ({placeholders}) OR destino_id IN ({placeholders}) "
        "LIMIT 1"
    )
    try:
        params = memory_ids + memory_ids
        db = await store.get_db()
        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchone()
        return rows is not None
    except Exception as e:
        logger.warning("Error verificando aristas en memory_edges: %s", e)
        return False


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

    # 2. Condición: Mensajes Conversacionales Triviales
    if (
        _is_casual_message(user_message)
        or payload.get("processing_type") == "conversational_only"
    ):
        logger.info(
            "[CONTEXT-RETRIEVER] Casual intent '%s' detected. "
            "Skipping semantical search.",
            intent,
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

        # Graph-RAG Transversal: Expansión de Grafo (ADR-0033 + ADR-0034)
        # Activación data-driven: si los fragmentos recuperados tienen aristas,
        # expandir el grafo sin discriminar por intent.
        # `expand_with_edges` ya incluye poda por accumulated_weight > 0.3
        # y límite de 8 fragmentos en la CTE recursiva (ver ADR-0034 sección 1b).
        if semantic_fragments:
            try:
                from src.memory.graph_search import expand_with_edges

                seed_ids = [item["id"] for item in semantic_fragments if "id" in item]
                has_edges = await _check_edges_exist(
                    store=manager.store, memory_ids=seed_ids
                )
                if has_edges:
                    graph_fragments = await expand_with_edges(
                        store=manager.store, seed_memory_ids=seed_ids, max_hops=2
                    )
                    logger.info(
                        "[CONTEXT-RETRIEVER] Graph-RAG expandido: "
                        "%d fragmentos de grafo",
                        len(graph_fragments),
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
