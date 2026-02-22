from typing import Any
from pydantic import BaseModel, Field


class MemorySummaryV1(BaseModel):
    summary: str = Field(default="Perfil activo.", description="Resumen de historia")
    buffer: list[dict[str, Any]] = Field(
        default_factory=list, description="Mensajes recientes"
    )
    last_updated: str | None = Field(default=None, description="ISO timestamp")
