# src/agents/orchestrator/routing/event_router.py
"""
EventRouter implementation.

Responsabilidad única: enrutamiento basado en event_type para eventos no-text.
Extraído del MasterOrchestrator para cumplir SRP.
"""

import logging
from typing import Any, cast

from src.agents.orchestrator.strategies import RoutingStrategy
from src.core.interfaces.specialist import SpecialistInterface
from src.core.registry import SpecialistRegistry
from src.core.schemas import GraphStateV2

logger = logging.getLogger(__name__)

PAYLOAD_KEY = "payload"
NEXT_NODE_KEY = "next_node"


class EventRouter(RoutingStrategy):
    """
    Enrutamiento para eventos no-text (audio, document, etc.).

    Responsabilidades:
    - Enrutamiento basado en capabilities de especialistas
    - Selección de especialista apropiado por event_type
    - Manejo de múltiples especialistas para mismo event_type
    """

    def __init__(self, specialist_registry: SpecialistRegistry):
        """
        Initialize router con specialist registry inyectado.

        Args:
            specialist_registry: Registry de especialistas disponibles
        """
        self._specialist_registry = specialist_registry

    async def route(self, state: GraphStateV2) -> str:
        """
        Enruta eventos no-text basado en capabilities.

        Args:
            state: Estado del grafo con event, payload, etc.

        Returns:
            str: Nombre del siguiente nodo o "__end__"
        """
        event = state["event"]
        event_type = event.event_type

        logger.info(f"EventRouter: enrutando evento '{event_type}'")

        # Inicializar payload si no existe
        if "payload" not in state:
            state["payload"] = {}

        # Encontrar especialistas que puedan manejar este tipo de evento
        capable_specialists = self._find_capable_specialists(event_type)

        if not capable_specialists:
            logger.warning(
                f"No se encontraron especialistas para evento '{event_type}'"
            )
            state["error_message"] = f"No hay especialistas para manejar '{event_type}'"
            return "__end__"

        # Seleccionar especialista apropiado
        selected_specialist = self._select_specialist(capable_specialists, event_type)
        state["payload"]["next_node"] = selected_specialist.name

        return selected_specialist.name

    def _find_capable_specialists(self, event_type: str) -> list[Any]:
        """
        Encuentra especialistas capaces de manejar el event_type.

        Args:
            event_type: Tipo de evento a enrutar

        Returns:
            Lista de especialistas con capabilities para el event_type
        """
        return [
            s
            for s in self._specialist_registry.get_all_specialists()
            if event_type in cast(SpecialistInterface, s).get_capabilities()
        ]

    def _select_specialist(self, capable_specialists: list, event_type: str) -> Any:
        """
        Selecciona especialista cuando hay múltiples opciones.

        Args:
            capable_specialists: Lista de especialistas capaces
            event_type: Tipo de evento para logging

        Returns:
            Especialista seleccionado
        """
        if len(capable_specialists) == 1:
            specialist = capable_specialists[0]
            logger.info(f"Enrutamiento directo para '{event_type}' → {specialist.name}")
            return specialist
        # Múltiples especialistas, tomar el primero por ahora
        # TODO: Implementar strategy más sofisticada de selección
        specialist = capable_specialists[0]
        logger.info(
            f"Múltiples especialistas para '{event_type}', tomando: {specialist.name}"
        )
        return specialist
