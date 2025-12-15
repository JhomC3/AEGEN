# src/core/routing_models.py
"""
Pydantic models para structured LLM output routing.

Responsabilidad única: definir estructuras de datos para decisiones 
de routing determinísticas basadas en análisis LLM structured.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class IntentType(str, Enum):
    """Tipos de intención reconocidos por el sistema."""
    CHAT = "chat"
    FILE_ANALYSIS = "file_analysis"
    SEARCH = "search"
    HELP = "help"
    TASK_EXECUTION = "task_execution"
    INFORMATION_REQUEST = "information_request"
    PLANNING = "planning"
    DOCUMENT_CREATION = "document_creation"


class EntityInfo(BaseModel):
    """Información de entidad extraída del mensaje."""
    type: str = Field(description="Tipo de entidad (email, url, document, etc.)")
    value: str = Field(description="Valor extraído de la entidad")
    confidence: float = Field(ge=0.0, le=1.0, description="Confianza en extracción")
    position: int | None = Field(None, description="Posición en texto original")


class RoutingDecision(BaseModel):
    """Decisión estruturada de routing basada en análisis LLM."""
    intent: IntentType = Field(description="Intención principal detectada")
    confidence: float = Field(ge=0.0, le=1.0, description="Confianza en clasificación")
    target_specialist: str = Field(description="Especialista objetivo para routing")
    requires_tools: bool = Field(description="Si requiere herramientas especializadas")

    # Información NLP integrada
    entities: list[EntityInfo] = Field(default_factory=list, description="Entidades extraídas")
    subintent: str | None = Field(None, description="Sub-intención específica")

    # Metadata para debugging y optimización
    processing_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata del procesamiento"
    )

    # Sugerencias para pipeline
    next_actions: list[str] = Field(
        default_factory=list,
        description="Acciones sugeridas post-routing"
    )


class RoutingContext(BaseModel):
    """Contexto adicional para decisiones de routing."""
    user_id: str
    session_id: str
    conversation_history_length: int = 0
    previous_intent: IntentType | None = None
    available_specialists: list[str] = Field(default_factory=list)
