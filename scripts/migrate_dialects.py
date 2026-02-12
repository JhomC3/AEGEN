import asyncio
import logging

from src.core.dependencies import initialize_global_resources, shutdown_global_resources
from src.core.profile_manager import user_profile_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def migrate_dialects():
    logger.info(
        "Iniciando migración de dialectos confirmados a preferencias explícitas..."
    )

    # Inicializar conexiones
    await initialize_global_resources()

    try:
        chat_ids = await user_profile_manager.list_all_profiles()
        logger.info(f"Encontrados {len(chat_ids)} perfiles para revisar.")

        migrated_count = 0
        for chat_id in chat_ids:
            profile = await user_profile_manager.load_profile(chat_id)

            localization = profile.get("localization", {})
            adaptation = profile.get("personality_adaptation", {})

            # Si la localización fue confirmada por el usuario y no hay preferencia explícita aún
            if localization.get("confirmed_by_user") and not adaptation.get(
                "preferred_dialect"
            ):
                dialect = localization.get("dialect")
                if dialect and dialect != "neutro":
                    logger.info(
                        f"Migrando dialecto '{dialect}' para chat_id: {chat_id}"
                    )
                    adaptation["preferred_dialect"] = dialect
                    profile["personality_adaptation"] = adaptation
                    await user_profile_manager.save_profile(chat_id, profile)
                    migrated_count += 1

        logger.info(f"Migración completada. {migrated_count} perfiles actualizados.")

    except Exception as e:
        logger.error(f"Error durante la migración: {e}")
    finally:
        await shutdown_global_resources()


if __name__ == "__main__":
    asyncio.run(migrate_dialects())
