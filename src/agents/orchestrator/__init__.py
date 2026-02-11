"""
MasterOrchestrator - Refactored Implementation Entry Point

Este archivo ahora importa la implementación refactorizada del MasterOrchestrator
que cumple con principios de Clean Architecture y SRP.
"""

import logging

# RESTORED: Refactored implementation with lazy initialization fix
from .factory import OrchestratorFactory, master_orchestrator
from .master_orchestrator import MasterOrchestrator

logger = logging.getLogger(__name__)

# Backward compatibility exports
__all__ = ["MasterOrchestrator", "OrchestratorFactory", "master_orchestrator"]

logger.info(
    "✅ MasterOrchestrator refactorizado con lazy initialization cargado exitosamente"
)
