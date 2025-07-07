from core.config import settings
from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters

TELEGRAM_TOKEN = settings.TELEGRAM_BOT_TOKEN.get_secret_value()


# Esta función es el "manejador" que procesará los mensajes de texto
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles incoming messages from Telegram."""
    # El objeto 'update.message' contiene toda la información del mensaje
    message = update.message
    if not message:
        return

    # 1. Recuperar el texto del mensaje
    text_content = message.text
    print(f"Texto recuperado: {text_content}")

    # 2. Recuperar información del chat
    chat_id = message.chat.id
    chat_type = (
        message.chat.type
    )  # Puede ser 'private', 'group', 'supergroup' o 'channel'
    print(f"Recibido en el chat ID {chat_id} (tipo: {chat_type})")

    # 3. Recuperar información del usuario que envió el mensaje
    user = message.from_user
    if not user:
        return
    user_id = user.id
    user_name = user.first_name
    print(f"Enviado por el usuario {user_name} (ID: {user_id})")

    # 4. Recuperar el ID único del mensaje (útil para responder o eliminar)
    message_id = message.message_id
    print(f"ID del mensaje: {message_id}")

    # Ejemplo de cómo usar la información recuperada para responder
    await context.bot.send_message(
        chat_id=chat_id, text=f"Recibí tu mensaje: '{text_content}'"
    )

    # 5. Recuperar un archivo (si lo hay)
    if message.document:
        document_file = await message.document.get_file()
        if message.document.file_name:
            await document_file.download_to_drive(
                f"descarga_{message.document.file_name}"
            )
            print(f"Documento '{message.document.file_name}' recuperado y guardado.")


# --- Configuración y ejecución del bot ---
def main() -> None:
    print("Iniciando bot...")
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # Se registra un manejador que reaccionará a CUALQUIER mensaje (texto, foto, audio, etc.)
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, message_handler))

    # Inicia el bot para que empiece a escuchar (polling)
    print("Bot escuchando mensajes...")
    app.run_polling()


if __name__ == "__main__":
    main()
