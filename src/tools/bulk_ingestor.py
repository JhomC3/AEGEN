# src/tools/bulk_ingestor.py
"""
Bulk Ingestor — Parsers para exportaciones de WhatsApp, Claude y ChatGPT.

Convierte historiales externos en conocimiento estructurado para AEGEN.
"""

import json
import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.memory.ingestion_pipeline import IngestionPipeline
from src.memory.sqlite_store import SQLiteStore

logger = logging.getLogger(__name__)


class WhatsAppParser:
    """Parser para exportaciones de WhatsApp (.txt)."""

    _MSG_PATTERN = re.compile(
        r"(\d{1,2}/\d{1,2}/\d{2,4})[, ]+(\d{1,2}:\d{2}(?::\d{2})?)\s*"
        r"[-–—]?\s*([^:]+):\s*(.+)"
    )

    async def parse(self, file_path: Path) -> list[dict]:
        messages: list[dict] = []
        content = file_path.read_text(encoding="utf-8")

        for line in content.split("\n"):
            match = self._MSG_PATTERN.match(line.strip())
            if match:
                date_str, time_str, sender, text = match.groups()
                try:
                    ts = self._parse_timestamp(date_str, time_str)
                except Exception:
                    ts = None

                role = "user" if sender != "MAGI" else "assistant"
                messages.append({
                    "role": role,
                    "content": text.strip(),
                    "sender": sender,
                    "timestamp": ts.isoformat() if ts else None,
                })

        logger.info(
            "[BULK-INGESTOR] WhatsApp: %d mensajes parseados de %s",
            len(messages),
            file_path.name,
        )
        return messages

    def _parse_timestamp(self, date_str: str, time_str: str) -> datetime:
        formats = [
            ("%d/%m/%Y", "%H:%M"),
            ("%d/%m/%Y", "%H:%M:%S"),
            ("%m/%d/%Y", "%H:%M"),
            ("%m/%d/%Y", "%H:%M:%S"),
            ("%d/%m/%y", "%H:%M"),
        ]
        for df, tf in formats:
            try:
                dt = datetime.strptime(f"{date_str} {time_str}", f"{df} {tf}")
                return dt.replace(tzinfo=UTC)
            except ValueError:
                continue
        raise ValueError(f"No se pudo parsear fecha: {date_str} {time_str}")


class ClaudeParser:
    """Parser para exportaciones de Claude (JSON)."""

    async def parse(self, file_path: Path) -> list[dict]:
        """
        Parsea un archivo de exportacion de Claude.

        Returns:
            Lista de mensajes con role, content, timestamp.
        """
        messages: list[dict] = []
        content = file_path.read_text(encoding="utf-8")

        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(
                "[BULK-INGESTOR] Claude: JSON invalido en %s: %s",
                file_path.name,
                e,
            )
            return messages

        if isinstance(data, list):
            for item in data:
                role = item.get("role", "user")
                text = item.get("content", "")
                if isinstance(text, list):
                    text = " ".join(
                        t.get("text", "") for t in text if isinstance(t, dict)
                    )
                messages.append({
                    "role": role,
                    "content": text.strip(),
                    "timestamp": item.get("timestamp"),
                })
        elif isinstance(data, dict):
            conversations = data.get("conversations", [data])
            for conv in conversations:
                for msg in conv.get("messages", []):
                    messages.append({
                        "role": msg.get("role", "user"),
                        "content": msg.get("content", "").strip(),
                        "timestamp": msg.get("timestamp"),
                    })

        logger.info(
            "[BULK-INGESTOR] Claude: %d mensajes parseados de %s",
            len(messages),
            file_path.name,
        )
        return messages


class ChatGPTParser:
    """Parser para exportaciones de ChatGPT (JSON)."""

    async def parse(self, file_path: Path) -> list[dict]:
        messages: list[dict] = []
        content = file_path.read_text(encoding="utf-8")

        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(
                "[BULK-INGESTOR] ChatGPT: JSON invalido en %s: %s",
                file_path.name,
                e,
            )
            return messages

        if isinstance(data, list):
            conversations = data
        elif isinstance(data, dict):
            conversations = data.get("conversations", [data])
        else:
            return messages

        for conv in conversations:
            title = conv.get("title", "")
            for msg in conv.get("mapping", {}).values():
                message = msg.get("message", {})
                if not message:
                    continue
                role = message.get("author", {}).get("role", "user")
                if role not in ("user", "assistant"):
                    continue
                parts = message.get("content", {}).get("parts", [])
                text = " ".join(str(p) for p in parts if p)
                if text:
                    messages.append({
                        "role": role,
                        "content": text.strip(),
                        "timestamp": message.get("create_time"),
                        "conversation_title": title,
                    })

        logger.info(
            "[BULK-INGESTOR] ChatGPT: %d mensajes parseados de %s",
            len(messages),
            file_path.name,
        )
        return messages


async def ingest_bulk_file(
    file_path: Path,
    chat_id: str,
    store: SQLiteStore | None = None,
    parser_type: str | None = None,
) -> dict[str, Any]:
    """
    Ingesta un archivo de exportacion masiva.

    Args:
        file_path: Ruta al archivo de exportacion.
        chat_id: ID del chat del usuario.
        store: SQLite store (inyectado).
        parser_type: Tipo de parser ('whatsapp', 'claude', 'chatgpt').
                     Si None, se detecta automaticamente.

    Returns:
        Dict con resultado de la ingesta.
    """
    from src.core.dependencies import get_sqlite_store

    if store is None:
        store = get_sqlite_store()

    ext = file_path.suffix.lower()
    name = file_path.name.lower()

    if parser_type is None:
        if ext == ".txt":
            parser_type = "whatsapp"
        elif "claude" in name:
            parser_type = "claude"
        elif "chatgpt" in name or "openai" in name:
            parser_type = "chatgpt"
        else:
            return {
                "error": "No se pudo detectar el tipo de archivo. "
                "Especifica parser_type.",
                "ingested": 0,
            }

    parsers: dict[str, WhatsAppParser | ClaudeParser | ChatGPTParser] = {
        "whatsapp": WhatsAppParser(),
        "claude": ClaudeParser(),
        "chatgpt": ChatGPTParser(),
    }

    parser = parsers.get(parser_type)
    if not parser:
        return {
            "error": f"Parser desconocido: {parser_type}",
            "ingested": 0,
        }

    messages: list[dict] = await parser.parse(file_path)
    if not messages:
        return {
            "error": "No se encontraron mensajes para parsear.",
            "ingested": 0,
        }

    pipeline = IngestionPipeline(store=store)
    ingested = 0

    for msg in messages:
        content = msg.get("content", "")
        if not content:
            continue

        metadata = {
            "source": f"bulk_{parser_type}",
            "sender": msg.get("sender", msg.get("role")),
        }
        if msg.get("timestamp"):
            metadata["created_at"] = msg["timestamp"]
        if msg.get("conversation_title"):
            metadata["conversation"] = msg["conversation_title"]

        count = await pipeline.process_text(
            chat_id=chat_id,
            text=content,
            memory_type="conversation",
            metadata=metadata,
        )
        ingested += count

    logger.info(
        "[BULK-INGESTOR] %s: %d/%d mensajes ingeridos para %s",
        parser_type,
        ingested,
        len(messages),
        chat_id,
    )

    return {
        "parser_type": parser_type,
        "total_messages": len(messages),
        "ingested": ingested,
        "source_file": file_path.name,
    }
