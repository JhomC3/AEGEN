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
    """Gestiona la consolidación de memoria."""

    def __init__(self) -> None:
        self.evolution_detector = EvolutionDetector(llm)

    async def should_consolidate(self, chat_id: str, message_count: int) -> bool:
        """Verifica si se cumplen las condiciones de consolidación."""
        if message_count >= 20:
            return True

        from src.memory.long_term_memory import long_term_memory

        buffer = await long_term_memory.get_buffer()
        last_activity = await buffer.get_last_activity(chat_id)

        if last_activity > 0:
            elapsed = time.time() - last_activity
            if elapsed > 21600:  # 6 horas
                return True
        return False

    async def consolidate_session(self, chat_id: str) -> None:
        """Proceso completo de consolidación."""
        logger.info("Consolidating session for %s", chat_id)
        from src.memory.fact_extractor import fact_extractor
        from src.memory.knowledge_base import knowledge_base_manager
        from src.memory.long_term_memory import long_term_memory

        buffer = await long_term_memory.get_buffer()
        raw_buffer = await buffer.get_messages(chat_id)

        if not raw_buffer:
            return

        await long_term_memory.update_memory(chat_id)

        try:
            cur_kb = await knowledge_base_manager.load_knowledge(chat_id)
            conv_text = "\n".join([f"{m['role']}: {m['content']}" for m in raw_buffer])

            # Extract and save facts
            upd_kb = await fact_extractor.extract_facts(conv_text, cur_kb)
            await knowledge_base_manager.save_knowledge(chat_id, upd_kb)
            await self._sync_user_name_to_profile(chat_id, upd_kb)

            # Extract and save milestones (State Management)
            from src.core.dependencies import get_sqlite_store
            from src.memory.milestone_extractor import milestone_extractor

            milestones = await milestone_extractor.extract_milestones(conv_text)
            if milestones:
                store = get_sqlite_store()
                for ms in milestones:
                    await store.state_repo.add_milestone(
                        chat_id=chat_id,
                        action=ms.action,
                        status=ms.status,
                        emotion=ms.emotion,
                        description=ms.description,
                    )
                    logger.info(
                        f"Hito guardado para {chat_id}: {ms.action} ({ms.status})"
                    )

        except Exception as e:
            logger.error("Error facts/milestones consolidation %s: %s", chat_id, e)

        new_data = await long_term_memory.get_summary(chat_id)
        summary = new_data["summary"]
        profile = await user_profile_manager.load_profile(chat_id)
        evolution = await self.evolution_detector.detect_evolution(profile, summary)
        if evolution:
            await apply_evolution(chat_id, profile, evolution)
        await log_session_to_memory(chat_id, summary, len(raw_buffer))

    async def _sync_user_name_to_profile(
        self, chat_id: str, knowledge: dict[str, Any]
    ) -> None:
        """Sincroniza el nombre detectado."""
        detected_name = knowledge.get("user_name")
        if not detected_name:
            return
        try:
            profile = await user_profile_manager.load_profile(chat_id)
            current_name = profile.get("identity", {}).get("name")
            if detected_name != current_name:
                logger.info("Sync Identity: %s -> %s", current_name, detected_name)
                profile["identity"]["name"] = detected_name
                await user_profile_manager.save_profile(chat_id, profile)
        except Exception as e:
            logger.error("Error syncing name %s: %s", chat_id, e)


consolidation_manager = ConsolidationManager()
