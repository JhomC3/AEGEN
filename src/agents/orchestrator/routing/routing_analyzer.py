# src/agents/orchestrator/routing/routing_analyzer.py
"""
Core LLM interaction para routing decisions.

Orquesta análisis LLM con function calling (optimizado) y coordina
post-processing usando componentes especializados.

Performance Fix: Migrado de llm.with_structured_output() a llm.bind_tools()
para eliminar bottleneck de 36+ segundos a <2 segundos (ADR-0009).
"""

import logging
from collections.abc import Sequence
from typing import Any, cast

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig

# Import Google API exceptions with fallback
try:
    from langchain_google_genai.common import GoogleAPICallError
except ImportError:
    # Fallback para entornos donde google.api_core no está disponible
    class ResourceExhaustedError(Exception):
        """Fallback ResourceExhausted exception"""

        pass

    class GoogleAPICallError(Exception):  # type: ignore
        """Fallback GoogleAPICallError exception"""

        pass


from src.agents.orchestrator.specialist_cache import SpecialistCache
from src.core.engine import create_observable_config, llm
from src.core.routing_models import EntityInfo, IntentType, RoutingDecision
from src.core.schemas import GraphStateV2

from .routing_patterns import IntentValidator, PatternExtractor, SpecialistMapper
from .routing_tools import route_user_message
from .routing_utils import extract_context_from_state

logger = logging.getLogger(__name__)


class RoutingAnalyzer:
    """
    Orquestador de análisis LLM para routing decisions.

    Coordina function calling LLM con componentes especializados
    para análisis robusto y post-processing inteligente.

    Performance optimized: Uses llm.bind_tools() instead of
    llm.with_structured_output() to eliminate 36+s latency bottleneck.
    """

    def __init__(self, routing_prompt: ChatPromptTemplate):
        """
        Inicializa analizador con componentes especializados.

        Args:
            routing_prompt: Prompt template configurado para function calling
        """
        # ✅ PERFORMANCE FIX: Function calling en lugar de structured output
        # Elimina bottleneck de 36+ segundos a <2 segundos
        routing_tools = [route_user_message]
        self._chain = routing_prompt | llm.bind_tools(cast(Sequence, routing_tools))

        # Mantiene componentes de post-processing existentes
        self._pattern_extractor = PatternExtractor()
        self._intent_validator = IntentValidator()
        self._specialist_mapper = SpecialistMapper()

    async def analyze(
        self, message: str, state: GraphStateV2, cache: SpecialistCache
    ) -> RoutingDecision:
        """
        Analiza mensaje y genera decisión de routing estructurada.

        Args:
            message: Mensaje del usuario a analizar
            state: Estado del grafo con contexto conversacional
            cache: Cache de especialistas disponibles

        Returns:
            RoutingDecision: Decisión estructurada con intent, confianza y entities

        Raises:
            Exception: Si falla análisis LLM o post-processing
        """
        available_tools = list(cache.get_tool_to_specialist_map().keys())
        context = extract_context_from_state(state)

        try:
            # ✅ PERFORMANCE FIX: Function calling en lugar de structured output
            # ✅ OBSERVABILITY: Add LLM tracking for routing calls
            config = create_observable_config(call_type="routing_analysis")
            response = await self._chain.ainvoke(
                {
                    "user_message": message,
                    "available_tools": available_tools,
                    "context": self._format_context_for_llm(context),
                },
                config=cast(RunnableConfig, config),
            )

            # Extraer resultado del function call
            decision_data = self._extract_tool_result(response)

            # Convertir a RoutingDecision manteniendo compatibilidad
            decision = self._build_routing_decision_from_data(decision_data)

            # Post-processing y validación (mantiene lógica existente)
            enhanced_decision = self._enhance_decision(decision, message, cache)

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
            return self._create_fallback_decision(message)
        except Exception as e:
            logger.error(
                f"Error inesperado en el análisis de enrutamiento: {e}", exc_info=True
            )
            return self._create_fallback_decision(message)

    def _enhance_decision(
        self, decision: RoutingDecision, message: str, cache: SpecialistCache
    ) -> RoutingDecision:
        """
        Mejora decisión LLM usando componentes especializados.

        Args:
            decision: Decisión base del LLM
            message: Mensaje original para análisis complementario
            cache: Cache para mapeo de especialistas

        Returns:
            RoutingDecision: Decisión mejorada con validation y mapping
        """
        # Extraer entidades adicionales con pattern extractor
        pattern_entities = self._pattern_extractor.extract_entities_from_text(message)
        decision.entities.extend(pattern_entities)

        # Ajustar confianza si hay evidencia clara del intent
        if self._intent_validator.has_clear_intent_evidence(message, decision.intent):
            decision.confidence = min(decision.confidence + 0.15, 1.0)

        # Validar que el especialista del LLM exista, sino usar fallback por intent
        available_specialists = list(cache.get_tool_to_specialist_map().values())

        if decision.target_specialist not in available_specialists:
            logger.warning(
                f"LLM sugirió '{decision.target_specialist}' no disponible. "
                f"Mapeando por intent: {decision.intent.value}"
            )
            decision.target_specialist = (
                self._specialist_mapper.map_intent_to_specialist(decision.intent, cache)
            )

        # Determinar requirement de tools
        decision.requires_tools = decision.intent != IntentType.CHAT

        return decision

    def _format_context_for_llm(self, context: dict[str, Any]) -> str:
        """
        Formatea contexto para inclusión en prompt LLM.

        Args:
            context: Diccionario con información contextual

        Returns:
            str: Contexto formateado para prompt
        """
        if not context:
            return "Sin contexto previo"

        parts = []

        if context.get("user_id"):
            parts.append(f"Usuario: {context['user_id']}")

        if context.get("history_length", 0) > 0:
            parts.append(f"Historial: {context['history_length']} mensajes")

        return " | ".join(parts) if parts else "Sesión nueva"

    def _create_fallback_decision(self, message: str) -> RoutingDecision:
        """
        Crea decisión fallback segura cuando falla análisis LLM.

        Args:
            message: Mensaje original para metadata básica

        Returns:
            RoutingDecision: Decisión fallback para chat specialist
        """
        return RoutingDecision(
            intent=IntentType.CHAT,
            confidence=0.5,  # Baja confianza indica fallback
            target_specialist="chat_specialist",
            requires_tools=False,
            entities=[],
            subintent=None,
            next_actions=[],  # Add required field
            processing_metadata={
                "fallback_reason": "LLM analysis failed",
                "message_length": len(message),
                "method": "function_calling_fallback",
            },
        )

    def _extract_tool_result(self, response) -> dict[str, Any]:
        """
        Extrae resultado del function call y retorna data dict.

        Args:
            response: Response del LLM con tool calls

        Returns:
            Dict: Data del function call para construir RoutingDecision
        """
        # Verificar si hay tool calls en la response
        if hasattr(response, "tool_calls") and response.tool_calls:
            tool_call = response.tool_calls[0]  # Primer tool call
            return tool_call.get("args", {})

        # Si es AIMessage con tool_calls
        if (
            hasattr(response, "additional_kwargs")
            and "tool_calls" in response.additional_kwargs
        ):
            tool_calls = response.additional_kwargs["tool_calls"]
            if tool_calls:
                return tool_calls[0].get("function", {}).get("arguments", {})

        # Fallback si no hay tool calls válidos
        logger.warning("No se encontraron tool calls válidos en response")
        return self._create_fallback_decision_data()

    def _build_routing_decision_from_data(
        self, decision_data: dict[str, Any]
    ) -> RoutingDecision:
        """
        Construye RoutingDecision desde function call data.

        Args:
            decision_data: Datos del function call

        Returns:
            RoutingDecision: Objeto compatible con sistema existente
        """
        # Extraer y validar intent
        intent_str = decision_data.get("intent", "chat")
        try:
            intent = IntentType(intent_str)
        except ValueError:
            logger.warning(f"Intent inválido '{intent_str}', usando CHAT")
            intent = IntentType.CHAT

        # Convertir entities de strings a EntityInfo objects
        entities_raw = decision_data.get("entities") or []
        entities = []
        for entity_str in entities_raw:
            if isinstance(entity_str, str) and entity_str.strip():
                entities.append(
                    EntityInfo(
                        type="extracted",
                        value=entity_str,
                        confidence=0.8,  # Default confidence para function call entities
                        position=None,
                    )
                )

        # Ensure next_actions is always a list
        next_actions = decision_data.get("next_actions")
        if next_actions is None:
            next_actions = []
        elif not isinstance(next_actions, list):
            next_actions = [next_actions] if next_actions else []

        return RoutingDecision(
            intent=intent,
            confidence=float(decision_data.get("confidence", 0.5)),
            target_specialist=decision_data.get("target_specialist", "chat_specialist"),
            requires_tools=bool(decision_data.get("requires_tools", False)),
            entities=entities,
            subintent=decision_data.get("subintent"),
            next_actions=next_actions,
            processing_metadata={
                **decision_data.get("processing_metadata", {}),
                "method": "function_calling",
            },
        )

    def _create_fallback_decision_data(self) -> dict[str, Any]:
        """
        Crea decision data fallback para casos de error.

        Returns:
            Dict: Datos básicos para RoutingDecision fallback
        """
        return {
            "intent": "chat",
            "confidence": 0.3,
            "target_specialist": "chat_specialist",
            "requires_tools": False,
            "entities": [],
            "next_actions": [],  # Add required field
            "processing_metadata": {
                "fallback_reason": "Function call extraction failed",
                "method": "function_calling_fallback",
            },
        }
