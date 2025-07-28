from datetime import datetime

from agents.communication.dto import GenericMessage
from agents.communication.handlers.base_handler import IMessageHandler
from vector_db.chroma_manager import ChromaManager


class TextHandler(IMessageHandler):
    """
    Manejador para procesar mensajes de texto.
    """

    def __init__(self, vector_db_manager: ChromaManager):
        self._vector_db_manager = vector_db_manager

    async def handle(self, message: GenericMessage) -> str:
        """
        Procesa un mensaje de texto, lo guarda en la base de datos vectorial
        y devuelve una confirmación.
        """
        text_info = {
            "type": "text",
            "content": message.content,
            **message.user_info,
            "timestamp": datetime.now().isoformat(),
        }
        await self._vector_db_manager.save(text_info)
        return f"📝 Texto recibido: '{message.content}'"
