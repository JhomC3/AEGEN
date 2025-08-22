# src/agents/orchestrator/routing/function_calling_router.py
"""
FunctionCallingRouter implementation.

Responsabilidad única: enrutamiento inteligente con LLM Function Calling.
Extraído del MasterOrchestrator para cumplir SRP y facilitar testing.
"""

import logging
from typing import Any, Dict

from langchain_core.messages import HumanMessage

from src.agents.orchestrator.specialist_cache import SpecialistCache
from src.agents.orchestrator.strategies import RoutingStrategy
from src.core.schemas import GraphStateV2

logger = logging.getLogger(__name__)

# Constantes extraídas para evitar magic strings
CHAT_SPECIALIST_NODE = "chat_specialist"
NEXT_NODE_KEY = "next_node"
TOOL_INVOCATION_KEY = "tool_invocation"
PAYLOAD_KEY = "payload"


class FunctionCallingRouter(RoutingStrategy):
    """
    Enrutamiento inteligente con LLM Function Calling.

    Responsabilidades:
    - Análisis de mensajes de usuario con LLM
    - Selección de herramientas especializadas
    - Fallback a ChatBot para conversación simple
    - Manejo de errores con graceful degradation
    """

    def __init__(self, specialist_cache: SpecialistCache):
        """
        Initialize router con cache de especialistas inyectado.

        Args:
            specialist_cache: Cache inicializado de especialistas y tools
        """
        self._cache = specialist_cache

    async def route(self, state: GraphStateV2) -> str:
        """
        Enruta mensaje usando Function Calling del LLM.

        Args:
            state: Estado del grafo con event, payload, etc.

        Returns:
            str: Nombre del siguiente nodo o "__end__"
        """
        event = state["event"]
        user_message = getattr(event, "content", "") or ""

        logger.info(f"FunctionCallingRouter: analizando '{user_message[:50]}...'")

        # Solo manejar eventos de texto
        if event.event_type != "text":
            logger.debug("Evento no-text, delegando a EventRouter")
            return "__end__"  # Will be handled by EventRouter

        # Inicializar payload si no existe
        if "payload" not in state:
            state["payload"] = {}

        # Verificar si hay herramientas disponibles
        if not self._cache.has_routable_tools():
            logger.info("No hay especialistas enrutables, fallback a ChatBot")
            self._set_next_node(state, CHAT_SPECIALIST_NODE)
            return self._get_next_node(state)

        try:
            # LLM decide si usar herramienta especializada
            llm_with_tools = self._cache.get_llm_with_tools()
            response = await llm_with_tools.ainvoke([
                HumanMessage(content=user_message)
            ])

            tool_calls = response.tool_calls or []

            # Manejo explícito de múltiples tool_calls
            if len(tool_calls) > 1:
                logger.warning(
                    f"LLM devolvió {len(tool_calls)} herramientas. "
                    f"Solo se procesará la primera."
                )

            if tool_calls:
                return self._handle_tool_selection(state, tool_calls[0])
            else:
                # LLM no eligió herramienta → conversación simple
                logger.info("Sin herramienta elegida, enrutando a ChatBot")
                self._set_next_node(state, CHAT_SPECIALIST_NODE)
                return self._get_next_node(state)

        except Exception as e:
            logger.error(f"Error en Function Calling: {e}, fallback a ChatBot")
            self._set_next_node(state, CHAT_SPECIALIST_NODE)
            return self._get_next_node(state)

    def _handle_tool_selection(
        self, state: GraphStateV2, tool_call: Dict[str, Any]
    ) -> str:
        """
        Maneja la selección de herramienta por parte del LLM.

        Args:
            state: Estado del grafo a modificar
            tool_call: Tool call seleccionado por el LLM

        Returns:
            str: Nombre del siguiente nodo
        """
        selected_tool_name = tool_call["name"]

        # Búsqueda O(1) usando mapeo pre-calculado
        tool_to_specialist_map = self._cache.get_tool_to_specialist_map()
        target_specialist = tool_to_specialist_map.get(selected_tool_name)

        if target_specialist:
            logger.info(f"LLM eligió: {selected_tool_name} → {target_specialist}")
            state["payload"]["next_node"] = target_specialist
            state["payload"]["tool_invocation"] = tool_call
            return target_specialist
        else:
            logger.warning(
                f"Herramienta '{selected_tool_name}' no mapea a especialista, "
                f"fallback a ChatBot"
            )
            self._set_next_node(state, CHAT_SPECIALIST_NODE)
            return self._get_next_node(state)

    def _set_next_node(self, state: GraphStateV2, node_name: str) -> None:
        """Establece el siguiente nodo en el estado."""
        if "payload" not in state:
            state["payload"] = {}
        state["payload"]["next_node"] = node_name

    def _get_next_node(self, state: GraphStateV2) -> str:
        """Obtiene el siguiente nodo del estado."""
        return state.get("payload", {}).get("next_node", "__end__")
