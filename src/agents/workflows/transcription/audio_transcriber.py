"""
Workflow para transcribir un archivo de audio recibido desde Telegram.

Este workflow orquesta las herramientas necesarias para descargar un archivo de audio,
transcribirlo a texto y enviar el resultado de vuelta al chat de origen.
"""

import logging
import tempfile
from pathlib import Path

from src.core.interfaces.workflow import IWorkflow
from src.core.registry import workflow_registry
from src.tools.speech_processing import transcribe_with_whisper
from src.tools.telegram_interface import telegram_tool

logger = logging.getLogger(__name__)


@workflow_registry.register("audio_transcription")
class AudioTranscriptionWorkflow(IWorkflow):
    """
    Orquesta la descarga, transcripción y respuesta de un audio de Telegram.
    """

    async def execute(self, event: dict) -> None:
        """
        Ejecuta el flujo de trabajo de transcripción.

        El evento esperado debe contener:
        - chat_id: El ID del chat de Telegram.
        - file_id: El ID del archivo de audio a procesar.
        """
        chat_id = event.get("chat_id")
        file_id = event.get("file_id")
        task_id = event.get("task_id", "N/A")  # Para logging contextual

        if not chat_id or not file_id:
            logger.error(
                f"[TaskID: {task_id}] Evento inválido para AudioTranscriptionWorkflow. "
                f"Falta 'chat_id' o 'file_id'. Evento: {event}"
            )
            return

        logger.info(
            f"[TaskID: {task_id}] Iniciando workflow de transcripción para el chat {chat_id}. "
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # 1. Descargar el archivo de audio
            audio_file_path = await telegram_tool.download_file_from_telegram(
                file_id=file_id, destination_folder=temp_path
            )

            if not audio_file_path:
                error_msg = "No se pudo descargar el archivo de audio de Telegram."
                logger.error(f"[TaskID: {task_id}] {error_msg}")
                await telegram_tool.send_telegram_message(
                    chat_id, f"Error: {error_msg}"
                )
                return

            # 2. Transcribir el audio a texto
            transcription_result = await transcribe_with_whisper.ainvoke(
                {"audio_path": str(audio_file_path)}
            )

            if not transcription_result or not transcription_result.get("transcript"):
                error_msg = "No se pudo transcribir el archivo de audio o el resultado está vacío."
                logger.error(f"[TaskID: {task_id}] {error_msg}")
                await telegram_tool.send_telegram_message(
                    chat_id, f"Error: {error_msg}"
                )
                return

            transcribed_text = transcription_result["transcript"]

            # 3. Enviar el texto transcrito de vuelta al usuario
            logger.info(
                f"[TaskID: {task_id}] Enviando transcripción al chat {chat_id}. "
            )

            response_text = f"Transcripción:\n\n---\n\n{transcribed_text}"

            success = await telegram_tool.send_telegram_message(chat_id, response_text)
            if success:
                logger.info(f"[TaskID: {task_id}] Workflow completado exitosamente.")
            else:
                logger.error(
                    f"[TaskID: {task_id}] Falló el envío del mensaje de respuesta."
                )
