from datetime import datetime
from pathlib import Path

from agents.communication.dto import GenericMessage
from agents.communication.handlers.base_handler import IMessageHandler
from tools.document_processing import DocumentProcessor
from tools.telegram_downloader import download_temp_file
from vector_db.chroma_manager import ChromaManager


class DocumentHandler(IMessageHandler):
    """
    Manejador para procesar mensajes que contienen documentos.
    """

    def __init__(
        self,
        document_processor: DocumentProcessor,
        vector_db_manager: ChromaManager,
    ):
        self._document_processor = document_processor
        self._vector_db_manager = vector_db_manager

    async def handle(self, message: GenericMessage) -> str:
        """
        Descarga un documento, extrae su contenido, lo guarda en la base de datos
        vectorial y devuelve una confirmación.
        """
        document_file = message.content
        file_name = message.file_name or "unknown_file"
        suffix = Path(file_name).suffix

        async with download_temp_file(document_file, suffix) as file_path:
            document_data = self._document_processor.process_document(
                file_path, file_name
            )

            file_info = {
                "type": "document",
                "file_name": file_name,
                **document_data,
                **message.user_info,
                "timestamp": datetime.now().isoformat(),
            }
            await self._vector_db_manager.save(file_info)

        return f"📄 Documento '{file_name}' recibido y procesado."
