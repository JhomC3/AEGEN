import logging
import time
from typing import Any

from src.core.engine import llm
from src.core.profile_manager import user_profile_manager
from src.memory.evolution_applier import apply_evolution
from src.memory.evolution_detector import EvolutionDetector
from src.memory.session_logger import log_session_to_memory

logger = logging.getLogger(__name__)


class ConsolidationManager:
    """
    Gestiona la consolidación de memoria: Buffer -> Resumen -> Perfil -> Nube.
    Trigger: N >= 20 mensajes O > 6 horas de inactividad.
    """

    def __init__(self):
        self.evolution_detector = EvolutionDetector(llm)

    async def should_consolidate(self, chat_id: str, message_count: int) -> bool:
        """
        4.2: Verifica si se cumplen las condiciones de consolidación.
        """
        # Regla 1: Más de 20 mensajes
        if message_count >= 20:
            return True

        # Regla 2: Más de 6 horas de inactividad
        from src.memory.long_term_memory import long_term_memory

        buffer = await long_term_memory.get_buffer()
        last_activity = await buffer.get_last_activity(chat_id)

        if last_activity > 0:
            elapsed = time.time() - last_activity
            if elapsed > 21600:  # 6 horas en segundos
                return True

        return False

    async def consolidate_session(self, chat_id: str):
        """
        4.3, 4.4, 4.5: Proceso completo de consolidación.
        """
        logger.info(f"Iniciando consolidación de sesión para {chat_id}")

        from src.memory.fact_extractor import fact_extractor
        from src.memory.knowledge_base import knowledge_base_manager
        from src.memory.long_term_memory import long_term_memory

        data = await long_term_memory.get_summary(chat_id)
        raw_buffer = data["buffer"]

        if not raw_buffer:
            return

        # 1. Generar resumen y actualizar memoria episódica
        await long_term_memory.update_memory(chat_id)

        # 2. EXTRAER HECHOS ESTRUCTURADOS (Hybrid Memory)
        try:
            current_knowledge = await knowledge_base_manager.load_knowledge(chat_id)

            # Convertir buffer a texto para el extractor
            conversation_text = "\n".join([
                f"{m['role']}: {m['content']}" for m in raw_buffer
            ])

            updated_knowledge = await fact_extractor.extract_facts(
                conversation_text, current_knowledge
            )
            await knowledge_base_manager.save_knowledge(chat_id, updated_knowledge)
            logger.info(f"Hechos estructurados actualizados para {chat_id}")

            # Sincronización explícita KB -> Profile
            await self._sync_user_name_to_profile(chat_id, updated_knowledge)

        except Exception as e:
            logger.error(
                f"Error extrayendo hechos durante consolidación para {chat_id}: {e}"
            )

        # 3. 4.4: Detectar evolución y actualizar perfil
        new_data = await long_term_memory.get_summary(chat_id)
        summary = new_data["summary"]
        profile = await user_profile_manager.load_profile(chat_id)

        evolution_data = await self.evolution_detector.detect_evolution(
            profile, summary
        )
        if evolution_data:
            await apply_evolution(chat_id, profile, evolution_data)

        # 4. 4.5: Almacenar Log de Sesión en SQLite (Local-First)
        await log_session_to_memory(chat_id, summary, len(raw_buffer))

    async def _sync_user_name_to_profile(
        self, chat_id: str, knowledge: dict[str, Any]
    ) -> None:
        """
        Sincroniza el nombre detectado en la Knowledge Base con el Perfil.
        """
        detected_name = knowledge.get("user_name")
        if not detected_name:
            return

        try:
            profile = await user_profile_manager.load_profile(chat_id)
            current_profile_name = profile.get("identity", {}).get("name")

            if detected_name != current_profile_name:
                logger.info(
                    f"Sync Identity: Updating profile name from '{current_profile_name}' to '{detected_name}'"
                )
                profile["identity"]["name"] = detected_name
                await user_profile_manager.save_profile(chat_id, profile)
        except Exception as e:
            logger.error(f"Error syncing user name to profile for {chat_id}: {e}")


# Singleton
consolidation_manager = ConsolidationManager()
