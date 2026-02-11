# src/agents/orchestrator/routing/routing_analyzer.py
"""
Core LLM interaction para routing decisions.

Orquesta análisis LLM con function calling (optimizado) y coordina
post-processing usando componentes especializados.
"""

import logging
from collections.abc import Sequence
from typing import cast

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig

# Import Google API exceptions with fallback
try:
    from langchain_google_genai.common import GoogleAPICallError
except ImportError:

    class ResourceExhaustedError(Exception):
        pass

    class GoogleAPICallError(Exception):  # type: ignore
        pass


from src.agents.orchestrator.specialist_cache import SpecialistCache
from src.core.engine import create_observable_config, llm
from src.core.routing_models import RoutingDecision
from src.core.schemas import GraphStateV2

from .routing_decision_builder import (
    build_routing_decision_from_data,
    create_fallback_decision,
    extract_tool_result,
)
from .routing_enhancer import RoutingEnhancer
from .routing_tools import route_user_message
from .routing_utils import extract_context_from_state, format_context_for_llm

logger = logging.getLogger(__name__)


class RoutingAnalyzer:
    """
    Orquestador de análisis LLM para routing decisions.
    """

    def __init__(self, routing_prompt: ChatPromptTemplate):
        # ✅ PERFORMANCE FIX: Function calling en lugar de structured output
        routing_tools = [route_user_message]
        self._chain = routing_prompt | llm.bind_tools(cast(Sequence, routing_tools))
        self._enhancer = RoutingEnhancer()

    async def analyze(
        self, message: str, state: GraphStateV2, cache: SpecialistCache
    ) -> RoutingDecision:
        """
        Analiza mensaje y genera decisión de routing estructurada.
        """
        available_tools = list(cache.get_tool_to_specialist_map().keys())
        context = extract_context_from_state(state)

        try:
            config = create_observable_config(call_type="routing_analysis")
            response = await self._chain.ainvoke(
                {
                    "user_message": message,
                    "available_tools": available_tools,
                    "context": format_context_for_llm(context),
                },
                config=cast(RunnableConfig, config),
            )

            # Extraer resultado del function call
            decision_data = extract_tool_result(response)

            # Convertir a RoutingDecision
            decision = build_routing_decision_from_data(decision_data)

            # Post-processing y validación
            enhanced_decision = self._enhancer.enhance_decision(
                decision, message, cache
            )

            logger.info(
                f"Análisis completado: {enhanced_decision.intent.value} → "
                f"{enhanced_decision.target_specialist} "
                f"(confianza: {enhanced_decision.confidence:.2f})"
            )

            return enhanced_decision

        except (ResourceExhaustedError, GoogleAPICallError) as e:
            logger.warning(
                f"Error de API de Google durante el enrutamiento: {e}. Se usará fallback."
            )
            return create_fallback_decision(message)
        except Exception as e:
            logger.error(
                f"Error inesperado en el análisis de enrutamiento: {e}", exc_info=True
            )
            return create_fallback_decision(message)
