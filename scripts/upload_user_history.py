import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv

# Cargar entorno
dotenv_path = Path(".env")
load_dotenv(dotenv_path=dotenv_path)

# Asegurar path de src
sys.path.append(str(Path.cwd()))

from src.tools.google_file_search import file_search_tool  # noqa: E402


async def upload_history(chat_id: str, file_path: str):
    print(f"📂 Preparando subida de historial para el usuario: {chat_id}")

    path = Path(file_path)
    if not path.exists():
        print(f"❌ Error: El archivo no existe en {file_path}")
        return

    # Usamos el prefijo 'manual/' para que el RAG lo priorice
    display_name = f"manual/history_backup_{path.name}"

    try:
        print(f"📤 Subiendo {file_path} como '{display_name}'...")
        uploaded_file = await file_search_tool.upload_file(
            file_path=str(path), chat_id=chat_id, display_name=display_name
        )
        print(f"✅ Éxito! Archivo subido: {uploaded_file.display_name}")
        print("🧠 MAGI ahora usará este archivo como contexto prioritario.")
    except Exception as e:
        print(f"❌ Error durante la subida: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(
            "Uso: uv run python3 scripts/upload_user_history.py <chat_id> <path_al_archivo>"
        )
        sys.exit(1)

    chat_id = sys.argv[1]
    file_path = sys.argv[2]

    asyncio.run(upload_history(chat_id, file_path))
