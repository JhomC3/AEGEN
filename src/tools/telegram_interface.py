import logging
from pathlib import Path
from typing import cast

import httpx
from langchain_core.tools import tool

from src.core.config import settings

logger = logging.getLogger(__name__)


class TelegramToolManager:
    def __init__(self) -> None:
        bot_token = settings.TELEGRAM_BOT_TOKEN
        if not bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN not configured")
        token = bot_token.get_secret_value().strip()
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.file_base_url = f"https://api.telegram.org/file/bot{token}"

    async def get_file_path(self, file_id: str) -> str | None:
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                url = f"{self.base_url}/getFile"
                resp = await client.post(url, data={"file_id": file_id})
                resp.raise_for_status()
                data = resp.json()
                if data.get("ok"):
                    return cast(str, data["result"]["file_path"])
                return None
            except Exception as e:
                logger.error("Error file path: %s", e)
                return None

    async def send_message(self, chat_id: str, text: str) -> bool:
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                url = f"{self.base_url}/sendMessage"
                payload: dict[str, str] = {
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": "Markdown",
                }
                resp = await client.post(url, data=payload)
                data = resp.json()
                if data.get("ok"):
                    return True
                desc = data.get("description", "")
                logger.warning("Telegram sendMessage failed: %s", desc)
                if "can't parse entities" in desc.lower() or "parse" in desc.lower():
                    payload.pop("parse_mode", None)
                    resp2 = await client.post(url, data=payload)
                    data2 = resp2.json()
                    if data2.get("ok"):
                        return True
                    logger.warning(
                        "Telegram sendMessage (plain text) also failed: %s",
                        data2.get("description", ""),
                    )
                return False
            except Exception as e:
                logger.error("Error sending: %s", e)
                return False

    async def send_chat_action(self, chat_id: str, action: str) -> bool:
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                url = f"{self.base_url}/sendChatAction"
                payload = {"chat_id": chat_id, "action": action}
                resp = await client.post(url, data=payload)
                return cast(bool, resp.json().get("ok", False))
            except Exception as e:
                logger.error("Error action: %s", e)
                return False

    async def download_file(self, file_id: str, dest_dir: Path) -> Path | None:
        file_path = await self.get_file_path(file_id)
        if not file_path:
            return None
        url = f"{self.file_base_url}/{file_path}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            filename = Path(file_path).name
            dest = dest_dir / filename
            dest.write_bytes(resp.content)
            return dest


@tool
async def download_telegram_file(file_id: str, save_path: Path) -> bool:
    """Helper to download a file."""
    path = await telegram_manager.get_file_path(file_id)
    if not path:
        return False
    url = f"{telegram_manager.file_base_url}/{path}"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        save_path.write_bytes(resp.content)
    return True


@tool
async def reply_to_telegram_chat(chat_id: str, text: str) -> bool:
    """Helper to reply."""
    return await telegram_manager.send_message(chat_id, text)


# Singleton instance (lazy)
_telegram_manager: TelegramToolManager | None = None


def get_telegram_manager() -> TelegramToolManager:
    """Lazy initialization to allow test mocking."""
    global _telegram_manager
    if _telegram_manager is None:
        _telegram_manager = TelegramToolManager()
    return _telegram_manager


telegram_manager = get_telegram_manager()
