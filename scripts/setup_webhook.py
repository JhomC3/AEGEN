import sys
import time

import httpx
from pyngrok import ngrok

from src.core.config import settings

TKN = (
    settings.TELEGRAM_BOT_TOKEN.get_secret_value()
    if settings.TELEGRAM_BOT_TOKEN
    else None
)
NGK = settings.NGROK_AUTHTOKEN.get_secret_value() if settings.NGROK_AUTHTOKEN else None
PORT = 8000


def setup_and_run() -> None:
    """Inicia ngrok y configura webhook."""
    if not TKN or not NGK:
        print("Faltan tokens en .env", file=sys.stderr)
        sys.exit(1)

    try:
        ngrok.set_auth_token(NGK)
        print(f"Iniciando ngrok puerto {PORT}...", file=sys.stderr)
        public_url = ngrok.connect(str(PORT)).public_url
        print(f"Túnel activo: {public_url}", file=sys.stderr)

        webhook_url = f"{public_url}/api/v1/webhooks/telegram"
        api_url = f"https://api.telegram.org/bot{TKN}/setWebhook"

        with httpx.Client() as client:
            resp = client.post(api_url, json={"url": webhook_url})
            resp.raise_for_status()
            if resp.json().get("ok"):
                print("✅ Webhook OK", file=sys.stderr)
            else:
                print("❌ Error webhook", file=sys.stderr)
                sys.exit(1)

        print("\n--- túnel activo. Ctrl+C para detener. ---", file=sys.stderr)
        while True:
            time.sleep(1)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
    finally:
        ngrok.kill()
        sys.exit(0)


if __name__ == "__main__":
    setup_and_run()
