# src/tools/multimodal_processor.py
"""
Procesador multimodal que delega el procesamiento de archivos
a herramientas especializadas existentes siguiendo el registry pattern.

Reutiliza la infraestructura existente en lugar de duplicar lógica.
"""

import logging
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from langchain_core.tools import tool

from src.tools.document_processing import process_document
from src.tools.image_processing import ImageToText
from src.tools.speech_processing import transcribe_audio

logger = logging.getLogger(__name__)

# Instancias de procesadores existentes
_image_processor = ImageToText()


# Registry de procesadores multimodales por extensión
PROCESSOR_REGISTRY: dict[str, Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]] = {
    # Documentos (delega a process_document)
    ".pdf": lambda args: process_document.ainvoke(args),
    ".docx": lambda args: process_document.ainvoke(args),
    ".txt": lambda args: process_document.ainvoke(args),
    ".md": lambda args: process_document.ainvoke(args),
    ".pptx": lambda args: process_document.ainvoke(args),
    ".xlsx": lambda args: process_document.ainvoke(args),
    ".csv": lambda args: process_document.ainvoke(args),
    # Imágenes (delega a ImageToText)
    ".png": lambda args: _image_processor.image_to_text_tool.ainvoke(args),
    ".jpg": lambda args: _image_processor.image_to_text_tool.ainvoke(args),
    ".jpeg": lambda args: _image_processor.image_to_text_tool.ainvoke(args),
    ".webp": lambda args: _image_processor.image_to_text_tool.ainvoke(args),
    # Audio (delega a transcribe_audio)
    ".mp3": lambda args: transcribe_audio.ainvoke(args),
    ".wav": lambda args: transcribe_audio.ainvoke(args),
    ".ogg": lambda args: transcribe_audio.ainvoke(args),
    ".m4a": lambda args: transcribe_audio.ainvoke(args),
}

logger.info(
    f"MultimodalProcessor initialized with support for: {list(PROCESSOR_REGISTRY.keys())}"
)


@tool
async def process_multimodal_file(file_path: str, file_name: str) -> dict[str, Any]:
    """
    Procesa archivos multimodales delegando a herramientas especializadas.

    Args:
        file_path: Ruta local al archivo
        file_name: Nombre original del archivo

    Returns:
        dict: Resultado del procesamiento o error
    """
    logger.info(f"Processing multimodal file: {file_name} at {file_path}")

    file_extension = Path(file_name).suffix.lower()
    processor_func = PROCESSOR_REGISTRY.get(file_extension)

    if not processor_func:
        error_msg = f"Unsupported file type: {file_extension}"
        logger.warning(error_msg)
        return {"error": error_msg}

    try:
        logger.info(f"Delegating to processor for '{file_extension}'")
        # Corregir la llamada para pasar un diccionario
        result = await processor_func({"file_path": file_path, "file_name": file_name})

        # Normalizar formato de salida
        if "transcript" in result:
            result["content"] = result.pop("transcript")

        logger.info(f"Successfully processed {file_name}")
        return result

    except Exception as e:
        error_msg = f"Error processing {file_name}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {"error": error_msg}
