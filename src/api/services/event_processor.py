import logging
import tempfile
from pathlib import Path
from typing import Any, cast

from src.agents.orchestrator.factory import master_orchestrator
from src.core import schemas
from src.core.profile_manager import user_profile_manager
from src.core.schemas import GraphStateV2
from src.core.session_manager import session_manager
from src.memory.long_term_memory import long_term_memory
from src.tools import telegram_interface

logger = logging.getLogger(__name__)


async def _download_event_files(
    event: schemas.CanonicalEventV1, temp_path: Path
) -> dict[str, Any]:
    """Descarga archivos (audio/imagen) del evento si existen."""
    payload_updates: dict[str, Any] = {}
    if not event.file_id:
        return payload_updates

    try:
        if event.event_type == "audio":
            path = await telegram_interface.download_telegram_file.ainvoke({
                "file_id": event.file_id,
                "destination_folder": str(temp_path),
            })
            payload_updates["audio_file_path"] = path
            logger.info(f"Audio descargado en {path}")
        elif event.event_type == "image":
            path = await telegram_interface.download_telegram_file.ainvoke({
                "file_id": event.file_id,
                "destination_folder": str(temp_path),
            })
            payload_updates["image_file_path"] = path
            logger.info(f"Imagen descargada en {path}")
    except Exception as e:
        logger.error(f"Error descargando archivo: {e}")

    return payload_updates


async def _update_user_context(event: schemas.CanonicalEventV1) -> None:
    chat_id = str(event.chat_id)
    if event.first_name:
        await user_profile_manager.seed_identity_from_platform(
            chat_id, event.first_name
        )
    if event.language_code:
        await user_profile_manager.update_localization(chat_id, event.language_code)


async def _load_session_context(chat_id: str) -> tuple[dict[str, Any], list[Any]]:
    existing_session = await session_manager.get_session(chat_id)
    if existing_session:
        return {
            "last_specialist": existing_session.get("last_specialist"),
            "last_intent": existing_session.get("last_intent"),
            "session_context": existing_session.get("session_context", {}),
        }, existing_session["conversation_history"]
    return {}, []


async def _run_orchestration(
    event: schemas.CanonicalEventV1,
    payload: dict[str, Any],
    conversation_history: list[Any],
    task_id: str,
) -> dict[str, Any]:
    initial_state = GraphStateV2(
        event=event,
        payload=payload,
        error_message=None,
        conversation_history=conversation_history,
        session_id=str(event.chat_id),
    )

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            file_payload = await _download_event_files(event, Path(temp_dir))
            initial_state["payload"].update(file_payload)
            logger.info(f"[TaskID: {task_id}] Invocando al MasterOrchestrator.")
            result = await master_orchestrator.run(initial_state)
            return cast(dict[str, Any], result)
    except Exception as e:
        logger.error(f"[TaskID: {task_id}] Fallo no controlado: {e}", exc_info=True)
        final_state = dict(initial_state)
        final_state["error_message"] = "Error inesperado al procesar solicitud."
        return final_state


async def _send_response(
    chat_id: str, final_state: dict[str, Any], task_id: str
) -> str:
    response_content = final_state.get("payload", {}).get("response")
    message = (
        final_state.get("error_message") or str(response_content)
        if response_content and str(response_content).strip()
        else "La tarea se completó, pero el agente generó una respuesta vacía."
    )
    try:
        await telegram_interface.reply_to_telegram_chat.ainvoke({
            "chat_id": chat_id,
            "text": message,
        })
    except Exception as e:
        logger.error(f"[TaskID: {task_id}] Error enviando respuesta: {e}")
    return message


async def _buffer_memory(
    chat_id: str, user_content: str, assistant_message: str
) -> None:
    try:
        await long_term_memory.store_raw_message(chat_id, "user", user_content)
        await long_term_memory.store_raw_message(
            chat_id, "assistant", assistant_message
        )
    except Exception as e:
        logger.error(f"Error al enviar mensajes al buffer: {e}")


async def process_event_task(event: schemas.CanonicalEventV1) -> None:
    """
    Tarea de fondo que orquesta el flujo de procesamiento para un evento canónico.
    """
    task_id = str(event.event_id)
    chat_id = str(event.chat_id)
    logger.info(f"[TaskID: {task_id}] Iniciando orquestación para chat {chat_id}.")

    await _update_user_context(event)
    payload, history = await _load_session_context(chat_id)

    final_state = await _run_orchestration(event, payload, history, task_id)

    message = await _send_response(chat_id, final_state, task_id)

    await session_manager.save_session(chat_id, final_state)

    user_text = event.content if isinstance(event.content, str) else "[No-Text]"
    await _buffer_memory(chat_id, user_text, message)

    logger.info(f"[TaskID: {task_id}] Orquestación finalizada.")
