# src/agents/specialists/__init__.py

# Importar todos los especialistas para que se registren en el SpecialistRegistry
# al iniciar la aplicación. El orden no importa.

from . import cbt_specialist, chat_agent, transcription_agent

__all__ = [
    "chat_agent",
    "transcription_agent",
    "cbt_specialist",
]
