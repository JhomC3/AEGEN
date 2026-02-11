import asyncio
import json
import logging
from datetime import datetime

from src.core.dependencies import get_sqlite_store
from src.memory.backup import CloudBackupManager
from src.memory.ingestion_pipeline import IngestionPipeline

logger = logging.getLogger(__name__)


async def log_session_to_memory(chat_id: str, summary: str, buffer_len: int) -> None:
    """Almacena Log de Sesión en SQLite (Local-First)."""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_content = {
            "chat_id": chat_id,
            "timestamp": timestamp,
            "summary": summary,
            "raw_messages_count": buffer_len,
            "type": "session_log",
        }

        store = get_sqlite_store()
        pipeline = IngestionPipeline(store)

        await pipeline.process_text(
            chat_id=chat_id,
            text=json.dumps(log_content, ensure_ascii=False),
            memory_type="document",
            metadata={"filename": f"session_{timestamp}.json", "type": "log"},
        )
        logger.info(f"Log de sesión guardado en SQLite para {chat_id}")

        # Trigger Cloud Backup (Fase 7)
        backup_mgr = CloudBackupManager(store)
        # Ejecutar en segundo plano para no bloquear la respuesta
        asyncio.create_task(backup_mgr.create_backup())

    except Exception as e:
        logger.warning(f"Error guardando log de sesión en SQLite para {chat_id}: {e}")
