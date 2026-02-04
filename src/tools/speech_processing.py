import logging
import os
from typing import Any

import aiofiles
from groq import Groq
from langchain_core.tools import tool

from src.core.config import settings

logger = logging.getLogger(__name__)

# Configurar Groq Client si la API KEY existe
groq_client = None
if settings.GROQ_API_KEY:
    groq_client = Groq(api_key=settings.GROQ_API_KEY.get_secret_value())

# Estadísticas a nivel de módulo
transcription_stats = {"transcriptions": 0, "errors": 0}


@tool
async def transcribe_audio(audio_path: str) -> dict[str, Any]:
    """
    Toma un archivo de audio y lo transcribe usando Groq Whisper API.
    Es mucho más rápido que Gemini File API para archivos cortos (< 25MB).
    """
    try:
        logger.info(f"Iniciando transcripción con Groq Whisper para: {audio_path}")

        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"El archivo de audio no existe: {audio_path}")

        if not groq_client:
            raise ValueError("GROQ_API_KEY no configurada.")

        # Determinar nombre de archivo
        filename = os.path.basename(audio_path)

        # 1. Solicitar transcripción a Groq
        logger.info(f"Enviando audio a Groq Whisper ({settings.AUDIO_MODEL})...")

        async with aiofiles.open(audio_path, "rb") as file:
            content = await file.read()
            # Groq espera el archivo en una tupla (filename, contents)
            transcription = groq_client.audio.transcriptions.create(
                file=(filename, content),
                model=settings.AUDIO_MODEL,
                response_format="json",  # "verbose_json" daría más info si fuera necesario
            )

        # 2. Procesar respuesta
        transcript = transcription.text

        # Intentar detectar el idioma si está disponible en x_groq (requiere verbose_json usualmente)
        # Por ahora lo dejamos como detectado genérico si no es verbose
        language = "detected"

        logger.info("Transcripción completa exitosamente.")
        transcription_stats["transcriptions"] += 1

        return {
            "transcript": transcript,
            "language": language,
        }

    except Exception as e:
        error_message = f"Error al transcribir audio con Groq: {e}"
        logger.error(f"{error_message}", exc_info=True)
        transcription_stats["errors"] += 1
        raise


@tool
def get_transcription_stats() -> dict[str, int]:
    """Devuelve las estadísticas de uso de la herramienta de transcripción."""
    return transcription_stats.copy()
