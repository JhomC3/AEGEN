"""Scheduler para tareas programadas de skills."""

import asyncio
import contextlib
import logging
from typing import Optional

from src.core.interfaces.bus import IEventBus
from src.personality.skill_loader import LoadedSkill

logger = logging.getLogger(__name__)


class CronScheduler:
    """
    Gestiona la ejecución periódica de skills basados en su configuración
    de 'schedule' en el manifest.
    """

    _instance: Optional["CronScheduler"] = None
    _event_bus: IEventBus | None
    _skills: list[LoadedSkill]
    _running: bool
    _task: asyncio.Task[None] | None

    def __new__(cls, event_bus: IEventBus | None = None) -> "CronScheduler":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._event_bus = event_bus
            cls._instance._skills = []
            cls._instance._running = False
            cls._instance._task = None
        return cls._instance

    def register_skills(self, skills: list[LoadedSkill]) -> None:
        """Registra los skills que tienen una programación activa."""
        self._skills = [
            s
            for s in skills
            if s.content.manifest.schedule and s.content.manifest.schedule.enabled
        ]
        logger.info(
            "CronScheduler: %d skills registrados para ejecución.", len(self._skills)
        )

    async def start(self) -> None:
        """Inicia el bucle de monitoreo del scheduler."""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("CronScheduler iniciado.")

    async def stop(self) -> None:
        """Detiene el bucle del scheduler."""
        self._running = False
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        logger.info("CronScheduler detenido.")

    async def _loop(self) -> None:
        """Bucle que comprueba las tareas cada minuto."""
        while self._running:
            # TODO: Integrar croniter para validación real de expresiones cron
            for _skill in self._skills:
                # Stub: Lógica de comprobación futura
                pass

            # Esperar hasta el siguiente minuto
            await asyncio.sleep(60)

    async def trigger_skill(self, skill: LoadedSkill) -> None:
        """Ejecuta un skill de forma proactiva."""
        if not skill.tool:
            return

        logger.info("Triggering scheduled skill: %s", skill.content.manifest.id)
        # TODO: Implementar ejecución proactiva enviando el resultado
