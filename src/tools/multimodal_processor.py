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

from src.tools.document_processing import DocumentProcessor
from src.tools.image_processing import ImageToText
from src.tools.speech_processing import transcribe_audio

logger = logging.getLogger(__name__)

# Instancias de procesadores existentes
_document_processor = DocumentProcessor()
_image_processor = ImageToText()


# Registry de procesadores multimodales por extensión
PROCESSOR_REGISTRY: dict[str, Callable[[str, str], Awaitable[dict[str, Any]]]] = {
    # Documentos (delega a DocumentProcessor)
    ".pdf": _document_processor.process_document,
    ".docx": _document_processor.process_document,
    ".txt": _document_processor.process_document,
    ".md": _document_processor.process_document,
    ".pptx": _document_processor.process_document,
    ".xlsx": _document_processor.process_document,
    ".csv": _document_processor.process_document,

    # Imágenes (delega a ImageToText)
    ".png": lambda path, name: _image_processor.image_to_text_tool(file_path=path),
    ".jpg": lambda path, name: _image_processor.image_to_text_tool(file_path=path),
    ".jpeg": lambda path, name: _image_processor.image_to_text_tool(file_path=path),
    ".webp": lambda path, name: _image_processor.image_to_text_tool(file_path=path),

    # Audio (delega a transcribe_audio)
    ".mp3": lambda path, name: transcribe_audio.ainvoke({"audio_path": path}),
    ".wav": lambda path, name: transcribe_audio.ainvoke({"audio_path": path}),
    ".ogg": lambda path, name: transcribe_audio.ainvoke({"audio_path": path}),
    ".m4a": lambda path, name: transcribe_audio.ainvoke({"audio_path": path}),
}

logger.info(f"MultimodalProcessor initialized with support for: {list(PROCESSOR_REGISTRY.keys())}")


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
        result = await processor_func(file_path, file_name)

        # Normalizar formato de salida
        if "transcript" in result:
            result["content"] = result.pop("transcript")

        logger.info(f"Successfully processed {file_name}")
        return result

    except Exception as e:
        error_msg = f"Error processing {file_name}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {"error": error_msg}
