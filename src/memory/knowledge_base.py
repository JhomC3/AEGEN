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
        Carga la bóveda desde Redis. Si no existe, intenta recuperación vía Gateway.
        """
        from src.core.dependencies import redis_connection
        from src.memory.cloud_gateway import cloud_gateway

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

        # --- AUTO-RECUPERACIÓN UNIFICADA (Gateway) ---
        logger.info(
            f"Conocimiento no encontrado en Redis para {chat_id}. Recuperando de Cloud..."
        )
        recovered_knowledge = await cloud_gateway.download_memory(
            chat_id, "knowledge_base"
        )

        if recovered_knowledge:
            await self.save_knowledge(chat_id, recovered_knowledge)
            return recovered_knowledge

        return self._get_default_knowledge()

    async def save_knowledge(self, chat_id: str, knowledge: dict[str, Any]):
        """Guarda la bóveda en Redis y sincroniza unificada con Google Cloud."""
        from src.core.dependencies import redis_connection
        from src.memory.cloud_gateway import cloud_gateway

        if redis_connection is None:
            return

        knowledge["last_updated"] = datetime.now().isoformat()
        key = self._redis_key(chat_id)

        try:
            # 1. Guardar en Redis
            payload = json.dumps(knowledge, ensure_ascii=False)
            await redis_connection.set(key, payload)

            # 2. Sincronización Unificada
            import asyncio

            asyncio.create_task(
                cloud_gateway.upload_memory(
                    chat_id=chat_id,
                    filename="knowledge_base",
                    data=knowledge,
                    mem_type="knowledge_base",
                )
            )

        except Exception as e:
            logger.error(f"Error guardando conocimiento para {chat_id}: {e}")

    async def sync_to_cloud(self, chat_id: str, knowledge: dict[str, Any]):
        """OBSOLETO: Se mantiene por compatibilidad."""
        from src.memory.cloud_gateway import cloud_gateway

        await cloud_gateway.upload_memory(
            chat_id, "knowledge_base", knowledge, "knowledge_base"
        )


# Singleton
knowledge_base_manager = KnowledgeBaseManager()
