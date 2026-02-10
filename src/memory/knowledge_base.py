# src/memory/knowledge_base.py
import json
import logging
from datetime import datetime
from typing import Any

from src.core.dependencies import get_sqlite_store
from src.memory.ingestion_pipeline import IngestionPipeline

logger = logging.getLogger(__name__)


class KnowledgeBaseManager:
    """
    Gestiona la Bóveda de Conocimiento Estructurado (Redis + Google Cloud).
    Contiene hechos precisos sobre el usuario (entidades, preferencias, datos médicos).
    """

    def __init__(self):
        logger.info("KnowledgeBaseManager initialized")

    def _get_default_knowledge(self) -> dict[str, Any]:
        """Estructura base de la Bóveda de Conocimiento."""
        return {
            "chat_id": None,
            "last_updated": datetime.now().isoformat(),
            "version": 1,
            "entities": [],
            "preferences": [],
            "medical": [],
            "relationships": [],
            "milestones": [],
        }

    def _redis_key(self, chat_id: str) -> str:
        return f"knowledge:{chat_id}"

    async def load_knowledge(self, chat_id: str) -> dict[str, Any]:
        """
        Carga la bóveda desde Redis. Si no existe, intenta recuperación desde SQLite.
        """
        from src.core.dependencies import redis_connection

        # 1. Intentar desde Redis
        if redis_connection:
            key = self._redis_key(chat_id)
            try:
                raw_data = await redis_connection.get(key)
                if raw_data:
                    if isinstance(raw_data, bytes):
                        raw_data = raw_data.decode("utf-8")
                    return json.loads(raw_data)
            except Exception as e:
                logger.error(
                    f"Error cargando conocimiento de Redis para {chat_id}: {e}"
                )

        # 2. Intentar desde SQLite (Búsqueda por tipo para obtener el más reciente)
        try:
            from src.memory.hybrid_search import HybridSearch

            store = get_sqlite_store()
            search = HybridSearch(store)
            results = await search.search_by_type(
                memory_type="fact", limit=1, chat_id=chat_id, namespace="user"
            )
            if results:
                # El contenido es el JSON de la KB
                kb_data = json.loads(results[0]["content"])
                return kb_data
        except Exception as e:
            logger.error(
                f"Error recuperando conocimiento de SQLite para {chat_id}: {e}"
            )

        return self._get_default_knowledge()

    async def save_knowledge(self, chat_id: str, knowledge: dict[str, Any]):
        """Guarda la bóveda en Redis y SQLite (Local-First)."""
        from src.core.dependencies import redis_connection

        knowledge["last_updated"] = datetime.now().isoformat()
        key = self._redis_key(chat_id)

        try:
            # 1. Guardar en Redis
            payload = json.dumps(knowledge, ensure_ascii=False)
            if redis_connection:
                await redis_connection.set(key, payload)

            # 2. Sincronización con SQLite (Nueva Memoria Local-First)
            try:
                store = get_sqlite_store()
                pipeline = IngestionPipeline(store)

                # Ingerir el conocimiento estructurado como un documento
                # Esto permite que sea recuperable vía búsqueda híbrida
                await pipeline.process_text(
                    chat_id=chat_id,
                    text=payload,
                    memory_type="fact",
                    metadata={"source": "knowledge_base", "type": "structured"},
                )
                logger.debug(f"Knowledge Base synchronized with SQLite for {chat_id}")
            except Exception as se:
                logger.warning(f"Error synchronizing Knowledge Base with SQLite: {se}")

        except Exception as e:
            logger.error(f"Error guardando conocimiento para {chat_id}: {e}")

    async def sync_to_cloud(self, chat_id: str, knowledge: dict[str, Any]):
        """OBSOLETO: No realiza ninguna acción en arquitectura Local-First."""
        pass


# Singleton
knowledge_base_manager = KnowledgeBaseManager()
