import asyncio
import logging
from typing import Any, Dict

import whisper
from core.config import settings
from langchain_core.tools import tool


class SpeechToText:
    def __init__(self, model: str = settings.DEFAULT_WHISPER_MODEL):
        self.logger = logging.getLogger(__name__)
        self.whisper_model = None
        self.model = model
        self.stats: dict[str, int] = {"transcriptions": 0, "errors": 0}
        self.logger.info(
            f"Iniciando herramienta de transcripción con modelo: {self.model} de Whisper"
        )

    def _get_whisper_model(self):
        if self.whisper_model is None:
            self.logger.info(f"Cargando modelo Whisper: {self.model}")
            self.whisper_model = whisper.load_model(self.model)
            self.logger.info(f"Modelo Whisper cargado: {self.model}")
        return self.whisper_model

    @tool
    async def transcribe_with_whisper(self, audio_path: str) -> Dict[str, Any]:
        """
        Toma un archivo de audio y lo transcribe usando Whisper y devuleve un texto completo de la transcripción.
        """
        try:
            self.logger.info(f"Iniciando transcripción para el archivo: {audio_path}")
            model_to_transcribe = self._get_whisper_model()
            result = await asyncio.to_thread(
                model_to_transcribe.transcribe(audio_path, fp16=False)
            )
            transcript: str = result["text"]
            language: str = result.get("language", "unknown")
            audio_info = {
                "transcript": transcript,
                "language": language,
            }

            self.logger.info(f"Transcripción completa para: {audio_path}")
            self.stats["transcriptions"] += 1
            return audio_info

        except Exception as e:
            error_message = f"Ocurrió un error al transcribir el audio: {e}"
            self.logger.error(
                f"Herramienta de Transcripción: {error_message}", exc_info=True
            )
            self.stats["errors"] += 1
            raise

    @tool
    def get_stats(self) -> dict[str, int]:
        return self.stats.copy()
