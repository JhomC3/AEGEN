from src.core.config import settings


def main() -> None:
    token = settings.TELEGRAM_BOT_TOKEN
    if token:
        val = token.get_secret_value()
        print(f"Token: {val[:5]}...")


if __name__ == "__main__":
    main()
