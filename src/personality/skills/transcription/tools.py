import logging

from langchain_core.tools import tool

from src.tools.speech_processing import transcribe_audio

logger = logging.getLogger(__name__)


@tool
async def transcription_tool(audio_file_path: str) -> str:
    """
    Usa esta herramienta para transcribir un archivo de audio a texto.
    Recibe la ruta local del archivo de audio y devuelve la transcripción.
    """
    logger.info("Herramienta de transcripción procesando: %s", audio_file_path)
    try:
        # Nota: transcribe_audio es un tool de LangChain en
        # src/tools/speech_processing.py
        result = await transcribe_audio.ainvoke({"audio_path": audio_file_path})
        transcription = result.get("transcript")
        if not isinstance(transcription, str):
            raise ValueError("La transcripción no devolvió un string válido.")
        logger.info(f"Transcripción exitosa para: {audio_file_path}")
        return transcription
    except Exception as e:
        error_message = f"Error durante la transcripción en la herramienta: {e}"
        logger.error(error_message, exc_info=True)
        return error_message


# Exportar para SkillLoader
SKILL_TOOL = transcription_tool
