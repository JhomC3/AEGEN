# src/agents/orchestrator_legacy.py
"""
LEGACY MasterOrchestrator - DEPRECATED

Este archivo contiene la implementación monolítica original del MasterOrchestrator.
Se mantiene temporalmente para compatibilidad durante la migración.

⚠️  DEPRECATED: Usar src/agents/orchestrator/factory.py para nueva implementación
⚠️  TODO: Eliminar este archivo después de completar migración y testing
"""

# Contenido original del MasterOrchestrator monolítico aquí
# (Mantenido para rollback en caso de problemas durante migración)

import logging

logger = logging.getLogger(__name__)


class LegacyMasterOrchestrator:
    """DEPRECATED - Solo para compatibility durante migración."""

    def __init__(self):
        logger.warning(
            "⚠️  Usando LegacyMasterOrchestrator DEPRECATED. "
            "Migrar a orchestrator.factory.OrchestratorFactory"
        )

    async def run(self, initial_state):
        raise NotImplementedError(
            "LegacyMasterOrchestrator no implementado. "
            "Usar nueva implementación refactorizada."
        )
