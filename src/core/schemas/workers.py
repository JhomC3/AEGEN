"""Schemas para la gestión de tareas asíncronas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from src.core.schemas.common import AgentResultStatus


class WorkerTask(BaseModel):
    """Representa una tarea delegada a un worker."""

    task_id: str
    skill_id: str
    chat_id: str
    status: AgentResultStatus = AgentResultStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    context: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class WorkerResult(BaseModel):
    """Resultado de la ejecución de un worker."""

    task_id: str
    skill_id: str
    chat_id: str
    success: bool
    output: Any
    error: str | None = None
    duration_seconds: float = 0.0
