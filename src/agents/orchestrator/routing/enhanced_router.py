# src/agents/orchestrator/routing/enhanced_router.py
"""
Enhanced FunctionCallingRouter con NLP integrado y structured output.

Responsabilidad única: análisis inteligente + routing determinístico
en single LLM call, eliminando duplicación y recursión.
"""

import logging

from src.agents.orchestrator.specialist_cache import SpecialistCache
from src.agents.orchestrator.strategies import RoutingStrategy
from src.core.routing_models import RoutingDecision
from src.core.schemas import GraphStateV2

from .routing_analyzer import RoutingAnalyzer
from .routing_prompts import build_routing_prompt
from .routing_utils import route_to_chat, update_state_with_decision

logger = logging.getLogger(__name__)

# Constantes
MIN_CONFIDENCE_THRESHOLD = 0.7


class EnhancedFunctionCallingRouter(RoutingStrategy):
    """
    Router inteligente con arquitectura modular y structured output.

    Orquesta componentes especializados para análisis robusto:
    routing prompt, LLM analyzer, pattern matching y specialist mapping.
    """

    def __init__(self, specialist_cache: SpecialistCache):
        self._cache = specialist_cache
        routing_prompt = build_routing_prompt()
        self._analyzer = RoutingAnalyzer(routing_prompt)

    async def route(self, state: GraphStateV2) -> str:
        """
        Análisis inteligente + routing en single call.

        Returns:
            str: Nombre del siguiente nodo specialist
        """
        event = state["event"]
        user_message = getattr(event, "content", "") or ""

        logger.info(f"EnhancedRouter: analizando '{user_message[:50]}...'")

        # Solo procesar eventos de texto
        if event.event_type != "text":
            return route_to_chat(state)

        # Verificar herramientas disponibles
        if not self._cache.has_routable_tools():
            return route_to_chat(state)

        try:
            # Análisis integrado con componentes especializados
            routing_decision = await self._analyzer.analyze(
                user_message, state, self._cache
            )

            # Aplicar decisión con validaciones
            return self._apply_routing_decision(state, routing_decision)

        except Exception as e:
            logger.error(f"Error en Enhanced Router: {e}", exc_info=True)
            return route_to_chat(state)

    def _apply_routing_decision(
        self, state: GraphStateV2, decision: RoutingDecision
    ) -> str:
        """Aplica la decisión de routing al state."""

        # Verificar confianza mínima
        if decision.confidence < MIN_CONFIDENCE_THRESHOLD:
            logger.warning(
                f"Baja confianza ({decision.confidence:.2f}), fallback a ChatBot"
            )
            return route_to_chat(state)

        # Verificar que el specialist esté disponible
        specialist_map = self._cache.get_tool_to_specialist_map()

        if decision.target_specialist in specialist_map.values():
            # Actualizar state y enrutar
            update_state_with_decision(state, decision)
            return decision.target_specialist
        else:
            logger.warning(f"Specialist '{decision.target_specialist}' no disponible")
            return route_to_chat(state)
