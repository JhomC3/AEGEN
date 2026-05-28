import logging
from typing import Any

logger = logging.getLogger(__name__)


async def trigger_session_consolidation(
    chat_id: str, session_data: dict[str, Any] | None
) -> None:
    """
    Explicitly triggers session consolidation to long-term memory.
    """
    if not session_data:
        return

    try:
        from src.memory.consolidation_worker import consolidation_manager

        # Usar el pipeline de consolidación unificado de background
        await consolidation_manager.consolidate_session(chat_id)
        logger.info(f"Consolidation triggered successfully for {chat_id}")
    except Exception as e:
        logger.error(f"Error triggering consolidation: {e}")
