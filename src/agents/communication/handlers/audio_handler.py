from datetime import datetime
from pathlib import Path

from agents.communication.dto import GenericMessage
from agents.communication.handlers.base_handler import IMessageHandler
from tools.speech_processing import SpeechToText
from tools.telegram_downloader import download_temp_file
from vector_db.chroma_manager import ChromaManager


class AudioHandler(IMessageHandler):
    """
    Manejador para procesar mensajes que contienen audio o notas de voz.
    """

    def __init__(
        self,
        speech_processor: SpeechToText,
        vector_db_manager: ChromaManager,
    ):
        self._speech_processor = speech_processor
        self._vector_db_manager = vector_db_manager

    async def handle(self, message: GenericMessage) -> str:
        """
        Descarga un archivo de audio, lo transcribe, lo guarda en la base de datos
        vectorial y devuelve una confirmación.
        """
        audio_file = message.content
        suffix = (
            ".ogg"
            if message.message_type == "voice"
            else Path(message.file_name or ".mp3").suffix
        )

        async with download_temp_file(audio_file, suffix) as file_path:
            audio_data = await self._speech_processor.transcribe_with_whisper(file_path)

            file_info = {
                "type": "audio",
                **audio_data,
                **message.user_info,
                "timestamp": datetime.now().isoformat(),
            }
            await self._vector_db_manager.save(file_info)

        return "🎵 Audio recibido y procesado."
