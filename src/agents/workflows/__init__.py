# src/agents/workflows/__init__.py

"""
Este paquete importa todos los módulos de workflow para que puedan ser
registrados automáticamente por el WorkflowRegistry al inicio de la aplicación.
"""

# Importa aquí cada nuevo workflow que crees.
from .transcription import audio_transcriber

__all__ = ["audio_transcriber"]
