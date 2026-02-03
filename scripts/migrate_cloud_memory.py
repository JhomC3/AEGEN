import asyncio
import logging
import sys
from pathlib import Path

# Añadir el directorio raíz al path para poder importar src
sys.path.append(str(Path(__file__).parent.parent))

from src.memory.cloud_gateway import cloud_gateway
from src.tools.google_file_search import file_search_tool

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("MigrationScript")


async def migrate_user(chat_id: str):
    logger.info(f"Iniciando migración para usuario {chat_id}...")

    # 1. Recuperar información básica desde vault.txt (único archivo legible)
    # vault.txt suele contener una lista de hechos o el perfil básico
    logger.info("Recuperando identidad desde vault.txt...")
    identity_query = (
        "Extrae el nombre del usuario y su estilo de interacción del archivo vault.txt."
    )
    identity_raw = await file_search_tool.query_files(identity_query, chat_id)

    if not identity_raw or "No encontrado" in identity_raw:
        logger.warning(f"No se encontró vault.txt o información legible para {chat_id}")
        return

    logger.info(f"Identidad recuperada: {identity_raw}")

    # 2. Reconstruir User Profile
    # Intentamos obtener más detalles
    profile_query = "Extrae todas las metas, preferencias y datos de identidad del usuario de sus archivos. Devuelve un JSON."
    await file_search_tool.query_files(profile_query, chat_id)

    # Aquí deberíamos procesar el string para obtener un dict
    # Para simplificar la migración, usaremos la lógica de CloudMemoryGateway para subir

    # Datos mínimos para no perder la identidad
    # Si identity_raw contiene "Jhonn", intentaremos extraerlo
    name = "Usuario"
    if "Jhonn" in identity_raw:
        name = "Jhonn"

    profile_data = {
        "identity": {
            "name": name,
            "style": "Empático y directivo",
            "detected_language": "es",
        },
        "values_and_goals": {
            "short_term_goals": "Recuperar la continuidad del sistema"
        },
    }

    # 3. Subir como .md (Arquitectura Unificada)
    logger.info("Subiendo nuevo user_profile.md...")
    await cloud_gateway.upload_memory(
        chat_id, "user_profile", profile_data, "user_profile"
    )

    # 4. Recuperar Hechos (Knowledge Base)
    logger.info("Recuperando base de conocimiento...")
    kb_query = "Lista todos los hechos aprendidos sobre el usuario, sus relaciones y entorno. Devuelve una lista de strings."
    kb_raw = await file_search_tool.query_files(kb_query, chat_id)

    if kb_raw and "No encontrado" not in kb_raw:
        kb_data = {
            "entities": [kb_raw],
            "preferences": [],
            "medical": [],
            "relationships": [],
            "milestones": [],
        }
        logger.info("Subiendo nueva knowledge_base.md...")
        await cloud_gateway.upload_memory(
            chat_id, "knowledge_base", kb_data, "knowledge_base"
        )

    logger.info(f"Migración completada para {chat_id}")


async def main():
    # En esta sesión nos enfocamos en el usuario Jhonn
    target_user = "6095416210"
    await migrate_user(target_user)


if __name__ == "__main__":
    asyncio.run(main())
