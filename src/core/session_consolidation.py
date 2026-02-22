import logging
from typing import Any

from src.memory.session_processor import SessionProcessor

logger = logging.getLogger(__name__)


async def trigger_session_consolidation(
    chat_id: str, session_data: dict[str, Any] | None
) -> None:
    """
    Explicitly triggers session consolidation to long-term memory.
    """
    if not session_data:
        return

    from src.core.dependencies import get_sqlite_store

    try:
        store = get_sqlite_store()
        processor = SessionProcessor(store)

        # Convert messages to dict if they are Pydantic models
        messages = [
            m.model_dump() if hasattr(m, "model_dump") else m
            for m in session_data.get("conversation_history", [])
        ]

        await processor.process_session(chat_id, messages)
        logger.info(f"Consolidation triggered successfully for {chat_id}")
    except Exception as e:
        logger.error(f"Error triggering consolidation: {e}")
