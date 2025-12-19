# src/agents/orchestrator_temp_fix.py
"""
Temporary fix para testing del refactor.
"""

import logging
from typing import Any

from src.core.schemas import GraphStateV2

logger = logging.getLogger(__name__)


class TempMasterOrchestrator:
    """Implementación temporal para debugging."""

    def __init__(self):
        logger.info("TempMasterOrchestrator inicializado para debugging")

    async def run(self, initial_state: GraphStateV2) -> dict[str, Any]:
        """
        Implementación temporal de run method.
        """
        logger.info("TempMasterOrchestrator.run() ejecutado")

        # Return estado sin cambios para debugging
        return {
            **initial_state,
            "payload": {
                **initial_state.get("payload", {}),
                "response": "TempMasterOrchestrator funcionando - refactor en progreso",
                "debug": "temp_orchestrator_active",
            },
        }


# Temporary instance
temp_master_orchestrator = TempMasterOrchestrator()
