# src/agents/specialists/__init__.py
import logging

logger = logging.getLogger(__name__)


def register_all_specialists() -> None:
    """Registra todos los especialistas. Llamado desde lifespan(), no al importar."""
    specialist_modules = [
        ("cbt_specialist", "cbt_specialist"),
        ("chat_agent", "chat_agent"),
        ("transcription_agent", "transcription_agent"),
    ]
    for module_name, display_name in specialist_modules:
        try:
            # Import dinámico para disparar el registro en SpecialistRegistry
            __import__(f"src.agents.specialists.{module_name}")
            logger.info("Especialista '%s' registrado exitosamente", display_name)
        except Exception:
            logger.exception(
                "Error registrando especialista '%s' — degradación suave", display_name
            )


__all__ = ["register_all_specialists"]
