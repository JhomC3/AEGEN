import logging
from typing import Any, Dict, Optional, Tuple

from agents.communication.dto import GenericMessage
from agents.communication.handlers.audio_handler import AudioHandler
from agents.communication.handlers.base_handler import IMessageHandler
from agents.communication.handlers.document_handler import DocumentHandler
from agents.communication.handlers.image_handler import ImageHandler
from agents.communication.handlers.text_handler import TextHandler
from core.config import settings
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    filters,
)
from tools.document_processing import DocumentProcessor
from tools.image_processing import ImageToText
from tools.speech_processing import SpeechToText
from vector_db.chroma_manager import ChromaManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class TelegramAgent:
    """
    Agente principal de Telegram que orquesta la recepción, procesamiento y
    respuesta de mensajes.
    """

    def __init__(self, token: str):
        self._app = ApplicationBuilder().token(token).build()
        self._handlers: Dict[str, IMessageHandler] = self._configure_handlers()

    def _configure_handlers(self) -> Dict[str, IMessageHandler]:
        """
        Inicializa y configura todos los servicios y manejadores de mensajes.
        Este es el "Composition Root" donde se realiza la inyección de dependencias.
        """
        # 1. Inicializar Servicios (Herramientas)
        vector_db = ChromaManager()
        speech_processor = SpeechToText()
        image_processor = ImageToText()
        document_processor = DocumentProcessor()

        # 2. Inicializar Manejadores (Estrategias) con sus dependencias
        return {
            "text": TextHandler(vector_db_manager=vector_db),
            "photo": ImageHandler(
                image_processor=image_processor, vector_db_manager=vector_db
            ),
            "audio": AudioHandler(
                speech_processor=speech_processor, vector_db_manager=vector_db
            ),
            "voice": AudioHandler(
                speech_processor=speech_processor, vector_db_manager=vector_db
            ),
            "document": DocumentHandler(
                document_processor=document_processor, vector_db_manager=vector_db
            ),
        }

    def _extract_message_info(
        self, update: Update
    ) -> Optional[Tuple[str, GenericMessage]]:
        """
        Extrae la información del Update de Telegram y la transforma en un GenericMessage.
        """
        message = update.message
        if not message or not message.from_user:
            return None

        user_info = {
            "user_id": message.from_user.id,
            "user_name": message.from_user.first_name or "Unknown",
            "chat_id": message.chat.id,
        }

        msg_type = ""
        content: Any = None
        file_name: Optional[str] = None

        if message.text:
            msg_type, content = "text", message.text
        elif message.photo:
            msg_type, content = "photo", message.photo[-1]
        elif message.audio:
            msg_type, content = "audio", message.audio
            file_name = message.audio.file_name
        elif message.voice:
            msg_type, content = "voice", message.voice
        elif message.document:
            msg_type, content = "document", message.document
            file_name = message.document.file_name
        else:
            return None  # Tipo de mensaje no soportado

        generic_message = GenericMessage(
            user_info=user_info,
            message_type=msg_type,
            content=content,
            file_name=file_name,
            metadata={"message_id": message.message_id, "chat_type": message.chat.type},
        )
        return msg_type, generic_message

    async def _dispatch_message(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Punto de entrada para todos los mensajes. Despacha al manejador correcto.
        """
        extracted_info = self._extract_message_info(update)
        if not extracted_info:
            logger.warning(
                "Could not extract a supported message type from the update."
            )
            return

        msg_type, generic_message = extracted_info
        user_info = generic_message.user_info

        logger.info(
            f"Message of type '{msg_type}' received from {user_info['user_name']} (ID: {user_info['user_id']})"
        )

        handler = self._handlers.get(msg_type)

        if not handler:
            response_text = f"❓ No hay un manejador implementado para mensajes de tipo '{msg_type}'."
            logger.warning(response_text)
        else:
            try:
                logger.info(f"Dispatching to handler: {handler.__class__.__name__}")
                response_text = await handler.handle(generic_message)
            except Exception as e:
                logger.error(
                    f"Unhandled error in handler {handler.__class__.__name__} for user {user_info['user_id']}: {e}",
                    exc_info=True,
                )
                response_text = (
                    "❌ Lo siento, ocurrió un error inesperado al procesar tu mensaje."
                )

        await context.bot.send_message(chat_id=user_info["chat_id"], text=response_text)

    def start(self) -> None:
        """
        Registra los manejadores y pone en marcha el bot de Telegram.
        """
        # Un único manejador que captura todos los tipos de mensaje relevantes
        all_filters = (
            filters.TEXT
            | filters.PHOTO
            | filters.AUDIO
            | filters.VOICE
            | filters.Document.ALL
        )
        self._app.add_handler(
            MessageHandler(all_filters & ~filters.COMMAND, self._dispatch_message)
        )

        logger.info("Starting Telegram bot with refactored architecture...")
        self._app.run_polling()


if __name__ == "__main__":
    telegram_token = settings.TELEGRAM_BOT_TOKEN.get_secret_value()
    if not telegram_token:
        raise ValueError(
            "El token del bot de Telegram no está configurado en las variables de entorno."
        )

    agent = TelegramAgent(token=telegram_token)
    agent.start()
