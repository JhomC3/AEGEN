from datetime import datetime

from agents.communication.dto import GenericMessage
from agents.communication.handlers.base_handler import IMessageHandler
from tools.image_processing import ImageToText
from tools.telegram_downloader import download_temp_file
from vector_db.chroma_manager import ChromaManager


class ImageHandler(IMessageHandler):
    """
    Manejador para procesar mensajes que contienen imágenes.
    """

    def __init__(
        self,
        image_processor: ImageToText,
        vector_db_manager: ChromaManager,
    ):
        self._image_processor = image_processor
        self._vector_db_manager = vector_db_manager

    async def handle(self, message: GenericMessage) -> str:
        """
        Descarga una imagen, extrae el texto, la guarda en la base de datos
        vectorial y devuelve una confirmación.
        """
        photo = message.content  # El contenido es el objeto de la foto
        async with download_temp_file(photo, ".jpg") as file_path:
            image_data = await self._image_processor.image_to_text_tool(file_path)

            file_info = {
                "type": "image",
                **image_data,
                **message.user_info,
                "timestamp": datetime.now().isoformat(),
            }
            await self._vector_db_manager.save(file_info)

        return "🖼️ Imagen recibida y procesada."
