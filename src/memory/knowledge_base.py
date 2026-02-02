# src/memory/knowledge_base.py
import json
import logging
from datetime import datetime
from typing import Any

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
        Carga la bóveda desde Redis. Si no existe, intenta recuperación vía RAG.
        """
        from src.core.dependencies import redis_connection
        from src.memory.recovery_manager import recovery_manager

        if redis_connection is None:
            return self._get_default_knowledge()

        key = self._redis_key(chat_id)
        try:
            raw_data = await redis_connection.get(key)
            if raw_data:
                if isinstance(raw_data, bytes):
                    raw_data = raw_data.decode("utf-8")
                return json.loads(raw_data)
        except Exception as e:
            logger.error(f"Error cargando conocimiento de Redis para {chat_id}: {e}")

        # --- AUTO-RECUPERACIÓN (Hybrid Memory Phase 2) ---
        logger.info(
            f"Conocimiento no encontrado en Redis para {chat_id}. Recuperando..."
        )
        recovered_knowledge = await recovery_manager.recover_knowledge(chat_id)

        if recovered_knowledge:
            await self.save_knowledge(chat_id, recovered_knowledge)
            return recovered_knowledge

        return self._get_default_knowledge()

    async def save_knowledge(self, chat_id: str, knowledge: dict[str, Any]):
        """Guarda la bóveda en Redis y sincroniza con Google Cloud."""
        from src.core.dependencies import redis_connection

        if redis_connection is None:
            return

        knowledge["last_updated"] = datetime.now().isoformat()
        key = self._redis_key(chat_id)

        try:
            # 1. Guardar en Redis
            payload = json.dumps(knowledge, ensure_ascii=False)
            await redis_connection.set(key, payload)

            # 2. Sync a Google Cloud (Background)
            import asyncio

            asyncio.create_task(self.sync_to_cloud(chat_id, knowledge))

        except Exception as e:
            logger.error(f"Error guardando conocimiento para {chat_id}: {e}")

    async def sync_to_cloud(self, chat_id: str, knowledge: dict[str, Any]):
        """Sincroniza la bóveda con Google File Search."""
        from src.tools.google_file_search import file_search_tool

        try:
            content = json.dumps(knowledge, indent=2, ensure_ascii=False)
            await file_search_tool.upload_from_string(
                content=content,
                filename="knowledge_base.json",
                chat_id=chat_id,
                mime_type="application/json",
            )
            logger.info(
                f"Bóveda de conocimiento sincronizada con Google Cloud para {chat_id}"
            )
        except Exception as e:
            logger.warning(f"Error en sync_to_cloud (knowledge) para {chat_id}: {e}")


# Singleton
knowledge_base_manager = KnowledgeBaseManager()
