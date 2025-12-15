import logging
import mimetypes
import os
from typing import Any

import google.generativeai as genai
from langchain_core.tools import tool

from src.core.config import settings

logger = logging.getLogger(__name__)

# Configurar Gemini API
if settings.GOOGLE_API_KEY:
    genai.configure(api_key=settings.GOOGLE_API_KEY.get_secret_value())

# Estadísticas a nivel de módulo
transcription_stats = {"transcriptions": 0, "errors": 0}


@tool
async def transcribe_audio(audio_path: str) -> dict[str, Any]:
    """
    Toma un archivo de audio, lo sube a Gemini API y devuelve la transcripción.
    Reemplaza a la implementación local de Whisper para ahorrar memoria (1GB RAM target).
    """
    try:
        logger.info(f"Iniciando transcripción con Gemini API para: {audio_path}")

        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"El archivo de audio no existe: {audio_path}")

        # Determinar MIME type
        mime_type, _ = mimetypes.guess_type(audio_path)
        if not mime_type:
            mime_type = "audio/mp3"  # Default fallback

        # 1. Subir archivo a Gemini (File API)
        logger.info(f"Subiendo archivo a Gemini File API ({mime_type})...")
        audio_file = genai.upload_file(path=audio_path, mime_type=mime_type)
        
        # 2. Configurar modelo
        model = genai.GenerativeModel("gemini-1.5-flash")
        
        # 3. Generar transcripción
        prompt = """
        Transcribe el siguiente archivo de audio exactamente como se escucha.
        Devuelve SOLO un objeto JSON con este formato:
        {
            "transcript": "texto transcrito aquí",
            "language": "código de idioma detectado (ej: es, en)"
        }
        """
        
        logger.info("Solicitando transcripción a Gemini 1.5 Flash...")
        response = model.generate_content(
            [prompt, audio_file],
            generation_config={"response_mime_type": "application/json"}
        )
        
        # 4. Procesar respuesta
        import json
        result = json.loads(response.text)
        
        # Limpiar archivo remoto (opcional, pero buena práctica si son muchos)
        # audio_file.delete() 
        
        logger.info(f"Transcripción completa. Idioma: {result.get('language')}")
        transcription_stats["transcriptions"] += 1
        
        return {
            "transcript": result.get("transcript", ""),
            "language": result.get("language", "unknown")
        }

    except Exception as e:
        error_message = f"Error al transcribir audio con Gemini: {e}"
        logger.error(f"{error_message}", exc_info=True)
        transcription_stats["errors"] += 1
        raise


@tool
def get_transcription_stats() -> dict[str, int]:
    """Devuelve las estadísticas de uso de la herramienta de transcripción."""
    return transcription_stats.copy()
