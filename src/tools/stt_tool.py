import os

import whisper
from langchain_core.tools import tool


@tool
def speech_to_text_tool(audio_path: str) -> str:
    """
    Toma un archivo de audio y lo transcribe usando Whisper y devuleve un texto completo de la transcripción.
    """
    whisper_model = whisper.load_model("base")
    try:
        print("Herramienta de Transcripción: Iniciando transcripción con Whisper...")
        result = whisper_model.transcribe(audio_path, fp16=False)
        transcript: str = result["text"]
        if not transcript or not isinstance(transcript, str):
            return ""
        return transcript

    except Exception as e:
        error_message = f"Ocurrió un error al transcribir el audio: {e}"
        print(f"Herramienta de Transcripción: {error_message}")
        raise e

    finally:
        if audio_path and os.path.exists(audio_path):
            print(
                f"Herramienta de Transcripción: Archivo temporal '{audio_path}' eliminado."
            )
