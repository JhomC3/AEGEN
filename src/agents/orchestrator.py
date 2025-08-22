# src/agents/orchestrator.py
"""
MasterOrchestrator - Refactored Implementation Entry Point

Este archivo ahora importa la implementación refactorizada del MasterOrchestrator
que cumple con principios de Clean Architecture y SRP.

La implementación monolítica original fue movida a orchestrator_legacy.py
"""

import logging

# RESTORED: Refactored implementation with lazy initialization fix
from .orchestrator.factory import OrchestratorFactory, master_orchestrator
from .orchestrator.master_orchestrator import MasterOrchestrator

logger = logging.getLogger(__name__)

# Backward compatibility exports
__all__ = ["MasterOrchestrator", "OrchestratorFactory", "master_orchestrator"]

logger.info(
    "✅ MasterOrchestrator refactorizado con lazy initialization cargado exitosamente"
)
