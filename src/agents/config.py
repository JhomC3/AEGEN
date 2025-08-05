from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Any

from langchain_core.runnables import RunnableConfig

from core.config import settings


@dataclass(kw_only=True)
class AgentConfig:
    """
    configuracion especifica para los agentes OnchainIQ.

    Contiene modelos, temperatura y otors parametros que lso agentes puede necesitar en tiempo de ejecucion.
    """

    search_model: str = "google_genai:gemini-2.5-flash"
    synthesis_model: str = "google_genai:gemini-2.5-flash"

    search_temperature: float = 0.1
    synthesis_temperature: float = 0.3

    @classmethod
    def from_runnable_config(cls, config: RunnableConfig | None = None) -> AgentConfig:
        """
        Crea una instancia de AgentConfig a partir de un RunnableConfig.
        """
        configurable = (
            config["configurable"] if config and "configurable" in config else {}
        )
        values: dict[str, Any] = {}
        for f in fields(cls):
            if f.init:
                field_name = f.name
                value = configurable.get(field_name)
                if value is None:
                    value = getattr(settings, field_name.upper(), None)
                values[field_name] = value
        return cls(**{k: v for k, v in values.items() if v is not None})
