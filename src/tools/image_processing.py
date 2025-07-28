import asyncio
import logging
from typing import Any, Dict

import pytesseract
from langchain_core.tools import tool
from PIL import Image


class ImageToText:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.stats: Dict[str, int] = {"image_processed": 0, "errors": 0}

    @tool
    async def image_to_text_tool(self, file_path: str) -> Dict[str, Any]:
        """Procesa un archivo de imagen para extraer texto (OCR)."""
        try:
            self.logger.info(f"Processing image {file_path}")
            image = Image.open(file_path)
            ocr_text = await asyncio.to_thread(
                pytesseract.image_to_string, image, lang="spa+eng"
            )
            image_info = {
                "text": ocr_text.strip(),
                "width": image.width,
                "height": image.height,
                "format": image.format,
            }
            self.logger.info(
                f"Image processed successfully, text length: {len(ocr_text)}"
            )
            self.stats["image_processed"] += 1
            return image_info

        except Exception as e:
            error_message = f"Ocurrió un error al procesar la imagen: {e}"
            self.logger.error(
                f"Error processing image {file_path}: {error_message}", exc_info=True
            )
            self.stats["error"] += 1
            raise

    @tool
    def get_stats(self) -> Dict[str, int]:
        return self.stats.copy()
