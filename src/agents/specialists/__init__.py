# src/agents/specialists/__init__.py
import logging

from src.core.registry import specialist_registry
from src.personality.skill_loader import SkillLoader

logger = logging.getLogger(__name__)


async def register_all_specialists() -> None:
    """
    Registra todos los especialistas dinámicamente desde el filesystem (Skills).
    Unifica personalidad y lógica de agentes según ADR-0026.
    """
    try:
        loader = SkillLoader()
        loaded_skills = await loader.discover_and_load()
        specialist_registry.register_from_loaded_skills(loaded_skills)

        # 2. Registrar en el Scheduler (ADR-0026 Fase 9)
        from src.agents.scheduler.cron_scheduler import CronScheduler

        CronScheduler().register_skills(loaded_skills)

        logger.info("Registro dinámico de skills completado.")
    except Exception:
        logger.exception("Error crítico durante la carga dinámica de especialistas")


__all__ = ["register_all_specialists"]
