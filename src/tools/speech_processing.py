import logging
from pathlib import Path
from typing import Any

import aiofiles
from groq import Groq
from langchain_core.tools import tool

from src.core.config import settings

logger = logging.getLogger(__name__)

# Configurar Groq Client
groq_client = None
if settings.GROQ_API_KEY:
    groq_client = Groq(api_key=settings.GROQ_API_KEY.get_secret_value())

# Estadísticas
transcription_stats = {"transcriptions": 0, "errors": 0}


@tool
async def transcribe_audio(audio_path: str) -> dict[str, Any]:
    """Transcribe audio usando Groq Whisper API."""
    try:
        audio_p = Path(audio_path)
        logger.info("Transcripción Groq para: %s", audio_p)

        if not audio_p.exists():
            raise FileNotFoundError(f"No existe: {audio_p}")

        if not groq_client:
            raise ValueError("GROQ_API_KEY no configurada.")

        # 1. Solicitar transcripción
        logger.info("Whisper model: %s", settings.AUDIO_MODEL)

        async with aiofiles.open(audio_p, "rb") as file:
            content = await file.read()
            transcription = groq_client.audio.transcriptions.create(
                file=(audio_p.name, content),
                model=settings.AUDIO_MODEL,
                response_format="json",
            )

        # 2. Procesar respuesta
        transcript = transcription.text
        language = "detected"

        logger.info("Transcripción completa.")
        transcription_stats["transcriptions"] += 1

        return {
            "transcript": transcript,
            "language": language,
        }

    except Exception as e:
        logger.error("Error transcribiendo: %s", e, exc_info=True)
        transcription_stats["errors"] += 1
        raise


@tool
def get_transcription_stats() -> dict[str, int]:
    """Estadísticas de transcripción."""
    return transcription_stats.copy()
