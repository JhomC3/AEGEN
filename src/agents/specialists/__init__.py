# src/agents/specialists/__init__.py

# Importar todos los especialistas para que se registren en el SpecialistRegistry
# al iniciar la aplicación. El orden no importa.

from . import chat_agent, transcription_agent
from .planner import agent as planner_agent

__all__ = ["chat_agent", "transcription_agent", "planner_agent"]
