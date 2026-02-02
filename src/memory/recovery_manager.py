# src/memory/recovery_manager.py
import json
import logging
from typing import Any

from src.core.engine import llm
from src.tools.google_file_search import file_search_tool

logger = logging.getLogger(__name__)


class RecoveryManager:
    """
    Sistema de Auto-Recuperación (Self-Healing) de Memoria.
    Reconstruye el estado del usuario usando Smart RAG cuando Redis falla.
    """

    def __init__(self):
        self.llm = llm
        logger.info("RecoveryManager inicializado")

    async def detect_cold_start(self, chat_id: str) -> bool:
        """
        Detecta si el usuario está en un estado de pérdida de memoria en Redis.
        """
        from src.core.dependencies import redis_connection

        if not redis_connection:
            return False

        profile_key = f"profile:{chat_id}"
        knowledge_key = f"knowledge:{chat_id}"

        # Si falta alguno de los dos, es un cold start potencial
        try:
            profile_exists = await redis_connection.exists(profile_key)
            knowledge_exists = await redis_connection.exists(knowledge_key)
            return not (profile_exists and knowledge_exists)
        except Exception as e:
            logger.error(f"Error detectando cold start para {chat_id}: {e}")
            return False

    async def recover_profile(self, chat_id: str) -> dict[str, Any] | None:
        """
        Reconstruye el perfil del usuario consultando la nube vía RAG.
        """
        logger.info(f"Intentando recuperación de PERFIL para {chat_id} vía RAG...")

        query = (
            "Extrae la información de perfil de este usuario: "
            "Nombre, estilo de comunicación preferido, país/localización, valores y metas. "
            "Responde en formato JSON puro."
        )

        try:
            # 1. Consultar a la nube
            raw_recovery = await file_search_tool.query_files(
                query, chat_id, tags=["USER_PROFILE", "VAULT"]
            )

            if not raw_recovery or "No encontrado" in raw_recovery:
                logger.warning(
                    f"No se encontró información de perfil en la nube para {chat_id}"
                )
                return None

            # 2. Refinar con LLM para asegurar estructura correcta
            recovery_prompt = (
                "A partir del siguiente fragmento de memoria recuperada, reconstruye un objeto de perfil de usuario. "
                "Usa el esquema estándar (identity, personality_adaptation, localization, values_and_goals). "
                "Si un dato no está, usa el valor por defecto del esquema.\n\n"
                f"MEMORIA RECUPERADA:\n{raw_recovery}\n\n"
                "RESPONDE SOLO EL JSON:"
            )

            response = await self.llm.ainvoke(recovery_prompt)
            profile_data = self._extract_json(str(response.content))

            if profile_data:
                logger.info(
                    f"Perfil recuperado exitosamente para {chat_id} (Nombre: {profile_data.get('identity', {}).get('name')})"
                )
                return profile_data

        except Exception as e:
            logger.error(f"Error en recuperación de perfil para {chat_id}: {e}")

        return None

    async def recover_knowledge(self, chat_id: str) -> dict[str, Any] | None:
        """
        Reconstruye la bóveda de conocimiento (hechos) vía RAG.
        """
        logger.info(
            f"Intentando recuperación de CONOCIMIENTO para {chat_id} vía RAG..."
        )

        query = (
            "Lista todos los hechos confirmados sobre este usuario: "
            "Entidades mencionadas, preferencias específicas, datos médicos o hitos de vida. "
            "Responde en formato JSON estructurado."
        )

        try:
            raw_recovery = await file_search_tool.query_files(
                query, chat_id, tags=["KNOWLEDGE", "FACTS"]
            )

            if not raw_recovery or "No encontrado" in raw_recovery:
                return None

            recovery_prompt = (
                "Convierte esta información recuperada en un objeto de Bóveda de Conocimiento (Knowledge Base). "
                "Debe tener las listas: entities, preferences, medical, relationships, milestones.\n\n"
                f"INFORMACIÓN:\n{raw_recovery}\n\n"
                "RESPONDE SOLO EL JSON:"
            )

            response = await self.llm.ainvoke(recovery_prompt)
            knowledge_data = self._extract_json(str(response.content))

            if knowledge_data:
                logger.info(f"Conocimiento recuperado exitosamente para {chat_id}")
                return knowledge_data

        except Exception as e:
            logger.error(f"Error en recuperación de conocimiento para {chat_id}: {e}")

        return None

    def _extract_json(self, text: str) -> dict[str, Any] | None:
        import re

        try:
            match = re.search(r"(\{[\s\S]*\})", text)
            if match:
                return json.loads(match.group(1))
            return json.loads(text)
        except Exception:
            return None


# Singleton
recovery_manager = RecoveryManager()
