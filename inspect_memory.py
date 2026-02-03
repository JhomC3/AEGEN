import asyncio
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

# Cargar variables de entorno explícitamente para evitar AssertionError
dotenv_path = Path(".env")
load_dotenv(dotenv_path=dotenv_path)

# Asegurar que el path de src esté disponible
sys.path.append(str(Path.cwd()))

from src.tools.google_file_search import file_search_tool  # noqa: E402


async def main():
    chat_id = "6095416210"

    # 1. Listar archivos en la nube
    try:
        files = await file_search_tool.list_files()
        print("\n--- [METADATOS EN GOOGLE CLOUD] ---")
        user_files = [f for f in files if f.display_name.startswith(f"{chat_id}/")]
        if not user_files:
            print("No se encontraron archivos para este usuario en la nube.")
        for f in user_files:
            print(
                f"- {f.display_name} (MIME: {f.mime_type}, State: {getattr(f, 'state', 'UNKNOWN')})"
            )
    except Exception as e:
        print(f"Error listando archivos: {e}")

    # 2. Intentar descargar desde la nube (vía RAG)
    try:
        from src.memory.cloud_gateway import cloud_gateway

        print("\n--- [RECUPERACIÓN VÍA RAG DESDE CLOUD] ---")
        profile = await cloud_gateway.download_memory(chat_id, "user_profile")
        knowledge = await cloud_gateway.download_memory(chat_id, "knowledge_base")

        # El vault es un archivo de texto plano, podemos consultarlo directamente
        vault_query = "Resume el contenido completo de vault.txt para este usuario."
        vault_content = await file_search_tool.query_files(vault_query, chat_id)

        print("\n--- [CONTENIDO: user_profile.md (Vía RAG)] ---")
        print(
            json.dumps(profile, indent=2, ensure_ascii=False)
            if profile
            else "No se pudo recuperar."
        )

        print("\n--- [CONTENIDO: knowledge_base.md (Vía RAG)] ---")
        print(
            json.dumps(knowledge, indent=2, ensure_ascii=False)
            if knowledge
            else "No se pudo recuperar."
        )

        print("\n--- [CONTENIDO: vault.txt (Resumen Vía RAG)] ---")
        print(vault_content or "No se pudo recuperar.")
    except Exception as e:
        print(f"Error recuperando de cloud: {e}")


if __name__ == "__main__":
    asyncio.run(main())
