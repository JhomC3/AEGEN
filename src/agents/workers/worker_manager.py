"""Gestor de tareas asíncronas para el Agentic Hub."""

import asyncio
import logging
import time
import uuid
from datetime import datetime
from typing import Any, Optional

from src.core.interfaces.bus import IEventBus
from src.core.schemas.common import AgentResultStatus
from src.core.schemas.workers import WorkerResult, WorkerTask

logger = logging.getLogger(__name__)


class WorkerManager:
    """
    Gestiona la ejecución, seguimiento y cancelación de tareas asíncronas
    generadas por los skills.
    """

    _instance: Optional["WorkerManager"] = None
    _tasks: dict[str, WorkerTask]
    _running_tasks: dict[str, asyncio.Task[None]]
    _event_bus: IEventBus | None

    def __new__(cls, event_bus: IEventBus | None = None) -> "WorkerManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tasks = {}
            cls._instance._running_tasks = {}
            cls._instance._event_bus = event_bus
        return cls._instance

    def __init__(self, event_bus: IEventBus | None = None) -> None:
        if event_bus:
            self._event_bus = event_bus

    async def spawn(
        self, skill_id: str, chat_id: str, tool: Any, context: dict[str, Any]
    ) -> str:
        """
        Crea y arranca una nueva tarea en segundo plano.
        """
        task_id = f"task_{uuid.uuid4().hex[:8]}"

        task_info = WorkerTask(
            task_id=task_id,
            skill_id=skill_id,
            chat_id=chat_id,
            context=context,
            status=AgentResultStatus.PENDING,
        )

        self._tasks[task_id] = task_info

        # Arrancar la ejecución
        bg_task: asyncio.Task[None] = asyncio.create_task(
            self._execute_wrapper(task_id, tool, context)
        )
        self._running_tasks[task_id] = bg_task

        logger.info("Tarea %s (Skill: %s) spawneada en background.", task_id, skill_id)
        return task_id

    async def _execute_wrapper(
        self, task_id: str, tool: Any, context: dict[str, Any]
    ) -> None:
        """Envoltorio para ejecutar la tarea, medir tiempo y manejar errores."""
        start_time = time.time()
        task_info = self._tasks[task_id]
        task_info.status = AgentResultStatus.PROCESSING
        task_info.started_at = datetime.now()

        success = False
        output = None
        error = None

        try:
            # Ejecutar el tool del skill
            output = await tool.ainvoke(context)
            success = True
            task_info.status = AgentResultStatus.SUCCESS
        except asyncio.CancelledError:
            logger.info("Tarea %s cancelada.", task_id)
            task_info.status = AgentResultStatus.ERROR
            error = "Tarea cancelada por el sistema o el usuario."
        except Exception as e:
            logger.exception("Error ejecutando worker task %s", task_id)
            task_info.status = AgentResultStatus.ERROR
            error = str(e)
        finally:
            duration = time.time() - start_time
            task_info.completed_at = datetime.now()
            task_info.error = error

            result = WorkerResult(
                task_id=task_id,
                skill_id=task_info.skill_id,
                chat_id=task_info.chat_id,
                success=success,
                output=output,
                error=error,
                duration_seconds=duration,
            )

            # Publicar resultado en el Event Bus
            if self._event_bus:
                topic = f"worker.done.{task_info.skill_id}"
                await self._event_bus.publish(topic, result.model_dump())
                logger.info(
                    "Resultado de tarea %s publicado en topic %s", task_id, topic
                )

            # Limpieza de tareas activas
            self._running_tasks.pop(task_id, None)

    def get_task_status(self, task_id: str) -> WorkerTask | None:
        """Consulta el estado de una tarea."""
        return self._tasks.get(task_id)

    async def cancel_task(self, task_id: str) -> bool:
        """Intenta cancelar una tarea activa."""
        if task_id in self._running_tasks:
            self._running_tasks[task_id].cancel()
            return True
        return False

    async def shutdown(self) -> None:
        """Cancela todas las tareas pendientes al apagar el sistema."""
        logger.info(
            "Apagando WorkerManager, cancelando %d tareas...", len(self._running_tasks)
        )
        for task in self._running_tasks.values():
            task.cancel()
        if self._running_tasks:
            await asyncio.gather(*self._running_tasks.values(), return_exceptions=True)
        self._running_tasks.clear()
