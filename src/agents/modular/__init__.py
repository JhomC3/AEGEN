# src/agents/modular/__init__.py
"""
Módulo de agentes modulares para Fase 3C.

Contiene implementaciones de BaseModularAgent que son:
- Simples (single responsibility)
- Async (filosofía obligatoria)
- Componibles (pueden trabajar juntos)
- Testeable (dependency injection)
"""

from .example_agent import ExampleModularAgent

__all__ = [
    "ExampleModularAgent",
]
