import asyncio
import logging
from typing import Any

import whisper
from langchain_core.tools import tool

from src.core.config import settings

logger = logging.getLogger(__name__)


class WhisperModelManager:
    """
    Gestiona la carga y el acceso al modelo Whisper.
    Asegura que el modelo se cargue una sola vez (patrón singleton).
    """

    _instance = None

    # Declarar atributos de instancia para que mypy los reconozca
    model_name: str
    logger: logging.Logger
    _whisper_model: Any = None

    def __new__(cls, model_name: str = settings.DEFAULT_WHISPER_MODEL):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.model_name = model_name
            cls._instance.logger = logging.getLogger(cls.__name__)
            cls._instance.logger.info(
                f"WhisperModelManager inicializado con el modelo: {model_name}"
            )
        return cls._instance

    async def get_model(self):
        """
        Carga el modelo Whisper si aún no está cargado y lo devuelve.
        La carga se realiza en un hilo separado para no bloquear el bucle de eventos.
        """
        if self._whisper_model is None:
            self.logger.info(f"Cargando el modelo Whisper: {self.model_name}...")
            self._whisper_model = await asyncio.to_thread(
                whisper.load_model, self.model_name
            )
            self.logger.info(f"Modelo Whisper '{self.model_name}' cargado con éxito.")
        return self._whisper_model


# Instancia única del gestor del modelo para toda la aplicación
whisper_manager = WhisperModelManager()

# Estadísticas a nivel de módulo para mantener un seguimiento
transcription_stats = {"transcriptions": 0, "errors": 0}


@tool
async def transcribe_with_whisper(audio_path: str) -> dict[str, Any]:
    """
    Toma un archivo de audio, lo transcribe usando Whisper y devuelve el texto.
    """
    try:
        logger.info(f"Iniciando transcripción para el archivo: {audio_path}")
        model = await whisper_manager.get_model()

        # Ejecutar la transcripción (que es bloqueante) en un hilo separado
        result = await asyncio.to_thread(model.transcribe, audio_path, fp16=False)

        transcript = result.get("text", "")
        language = result.get("language", "unknown")

        audio_info = {
            "transcript": transcript,
            "language": language,
        }

        logger.info(f"Transcripción completa para: {audio_path}")
        transcription_stats["transcriptions"] += 1
        return audio_info

    except Exception as e:
        error_message = f"Ocurrió un error al transcribir el audio: {e}"
        logger.error(f"{error_message}", exc_info=True)
        transcription_stats["errors"] += 1
        # Propagar la excepción para que el workflow la maneje
        raise


@tool
def get_transcription_stats() -> dict[str, int]:
    """Devuelve las estadísticas de uso de la herramienta de transcripción."""
    return transcription_stats.copy()
