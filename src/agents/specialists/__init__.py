# src/agents/specialists/__init__.py

# Importar todos los especialistas para que se registren en el SpecialistRegistry
# al iniciar la aplicación. El orden no importa.

from . import cbt_specialist, chat_agent, file_handler_specialist, transcription_agent
from .planner import agent as planner_agent

__all__ = [
    "chat_agent",
    "transcription_agent",
    "planner_agent",
    "cbt_specialist",
    "file_handler_specialist",
]
