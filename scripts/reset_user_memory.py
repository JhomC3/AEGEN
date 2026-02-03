import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Cargar entorno
dotenv_path = Path(".env")
load_dotenv(dotenv_path=dotenv_path)

# Asegurar path de src
sys.path.append(str(Path.cwd()))

from src.tools.google_file_search import file_search_tool  # noqa: E402


async def reset_user(chat_id: str):
    print(f"🚀 Iniciando reset total para el usuario: {chat_id}")

    # 1. Limpieza en Google Cloud
    print("\n--- [1/2] LIMPIEZA EN GOOGLE CLOUD ---")
    try:
        files = await file_search_tool.list_files()
        user_files = [f for f in files if f.display_name.startswith(f"{chat_id}/")]

        if not user_files:
            print("No se encontraron archivos en la nube.")
        else:
            print(f"Detectados {len(user_files)} archivos. Eliminando...")
            for f in user_files:
                try:
                    await file_search_tool.delete_file(f.name)
                    print(f"✅ Eliminado: {f.display_name}")
                except Exception as e:
                    print(f"❌ Error eliminando {f.display_name}: {e}")
    except Exception as e:
        print(f"Error accediendo a la File API: {e}")

    # 2. Limpieza en Redis (vía librería python-redis)
    print("\n--- [2/2] LIMPIEZA EN REDIS ---")
    try:
        import redis

        # Intentamos conectar usando la configuración de .env o default
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", 6379))

        r = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)

        keys_to_clear = [
            f"profile:{chat_id}",
            f"knowledge:{chat_id}",
            f"memory:summary:{chat_id}",
            f"buffer:{chat_id}",
            f"session:{chat_id}",
            f"specialist_history:{chat_id}",
        ]

        for key in keys_to_clear:
            if r.delete(key):
                print(f"✅ Llave Redis eliminada: {key}")
            else:
                print(f"⚪ Llave no encontrada (ya limpia): {key}")

    except Exception as e:
        print(f"❌ Error conectando a Redis: {e}")

    print(
        f"\n✨ Reset completado para {chat_id}. MAGI ahora te ve como un usuario nuevo."
    )


if __name__ == "__main__":
    chat_id = "6095416210"
    asyncio.run(reset_user(chat_id))
