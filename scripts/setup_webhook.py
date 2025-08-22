# scripts/setup_webhook.py
import sys
import time

import httpx
from pyngrok import ngrok

# Importar el objeto de configuración centralizado, que ya carga .env
from src.core.config import settings

# Acceder a la configuración desde el objeto settings
TELEGRAM_BOT_TOKEN = (
    settings.TELEGRAM_BOT_TOKEN.get_secret_value()
    if settings.TELEGRAM_BOT_TOKEN
    else None
)
NGROK_AUTHTOKEN = (
    settings.NGROK_AUTHTOKEN.get_secret_value() if settings.NGROK_AUTHTOKEN else None
)
PORT = 8000


def setup_and_run():
    """
    Inicia un túnel ngrok, configura el webhook de Telegram y mantiene el túnel abierto.
    """
    if not TELEGRAM_BOT_TOKEN:
        print(
            "Error: La variable de entorno TELEGRAM_BOT_TOKEN no está definida.",
            file=sys.stderr,
        )
        sys.exit(1)

    if not NGROK_AUTHTOKEN:
        print(
            "Error: La variable de entorno NGROK_AUTHTOKEN no está definida.",
            file=sys.stderr,
        )
        print(
            "Por favor, obtén tu token de https://dashboard.ngrok.com/get-started/your-authtoken y añádelo a tu archivo .env",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        # Configurar el authtoken de ngrok
        ngrok.set_auth_token(NGROK_AUTHTOKEN)

        # Iniciar el túnel ngrok
        print(
            f">>> Iniciando túnel de ngrok hacia el puerto {PORT}...", file=sys.stderr
        )
        public_url = ngrok.connect(PORT).public_url
        print(f"\033[92m>>> Túnel activo: {public_url}\033[0m", file=sys.stderr)

        # Configurar el webhook en Telegram
        webhook_url = f"{public_url}/api/v1/webhooks/telegram"
        api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook"

        print(
            f">>> Configurando webhook en Telegram para la URL: {webhook_url}",
            file=sys.stderr,
        )

        with httpx.Client() as client:
            response = client.post(api_url, json={"url": webhook_url})
            response.raise_for_status()

            response_data = response.json()
            if response_data.get("ok"):
                print(
                    f"\033[92m>>> Webhook configurado exitosamente: {response_data.get('description')}\033[0m",
                    file=sys.stderr,
                )
            else:
                print(
                    f"\033[91mError al configurar el webhook: {response_data}\033[0m",
                    file=sys.stderr,
                )
                sys.exit(1)

        print(
            "\n--- El túnel de ngrok está activo. Presiona Ctrl+C para detenerlo. ---",
            file=sys.stderr,
        )
        while True:
            time.sleep(1)

    except Exception as e:
        print(f"\033[91mOcurrió un error: {e}\033[0m", file=sys.stderr)
    finally:
        print("\n>>> Cerrando túneles de ngrok...", file=sys.stderr)
        ngrok.kill()
        print(">>> Todos los túneles han sido cerrados.", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    setup_and_run()
