# src/agents/orchestrator/routing/enhanced_router.py
"""
Enhanced FunctionCallingRouter con NLP integrado y structured output.

Responsabilidad única: análisis inteligente + routing determinístico
en single LLM call, eliminando duplicación y recursión.
"""

import logging

from src.agents.orchestrator.specialist_cache import SpecialistCache
from src.agents.orchestrator.strategies import RoutingStrategy
from src.core.routing_models import IntentType, RoutingDecision
from src.core.schemas import GraphStateV2

from .routing_analyzer import RoutingAnalyzer
from .routing_prompts import build_routing_prompt
from .routing_utils import (
    detect_explicit_command,
    is_conversational_only,
    route_to_chat,
    update_state_with_decision,
)
from .therapeutic_session import should_maintain_therapeutic_session

logger = logging.getLogger(__name__)

# Constantes de confianza para sistema multi-nivel
MIN_CONFIDENCE_THRESHOLD = 0.5
MODERATE_CONFIDENCE_THRESHOLD = 0.85
LOW_CONFIDENCE_THRESHOLD = 0.60


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

        # ✅ FAST PATH
        if is_conversational_only(user_message):
            logger.info("Fast Path: Mensaje conversacional detectado -> Chat")
            return route_to_chat(state)

        # ✅ EXPLICIT COMMANDS
        explicit_target = detect_explicit_command(user_message)
        if explicit_target:
            logger.info(f"Comando explícito detectado -> {explicit_target}")
            if "payload" not in state:
                state["payload"] = {}
            state["payload"]["next_node"] = explicit_target
            return explicit_target

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

        # A.4: Lógica de Stickiness (Afinidad)
        # Boost si es el mismo especialista anterior y confianza media.
        last_specialist = state.get("payload", {}).get("last_specialist")
        if (
            last_specialist
            and decision.target_specialist == last_specialist
            and 0.5 <= decision.confidence < 0.8
        ):
            old_conf = decision.confidence
            decision.confidence = 0.8  # Boost a confianza moderada-alta
            logger.info(
                f"Stickiness: Boost de confianza para {last_specialist} "
                f"({old_conf:.2f} -> {decision.confidence:.2f})"
            )

        # ADR-0024: Protección de Sesión Terapéutica
        if should_maintain_therapeutic_session(state, decision):
            decision.target_specialist = "cbt_specialist"
            decision.next_actions = [
                "handle_resistance",
                "validate_frustration",
                "pacing_one_step",
            ]
            return self._route_to_specialist(state, decision)

        # Verificar confianza mínima global
        if decision.confidence < MIN_CONFIDENCE_THRESHOLD:
            logger.warning(
                "Confianza muy baja (%.2f < %.2f), fallback a ChatBot. Intent: %s",
                decision.confidence,
                MIN_CONFIDENCE_THRESHOLD,
                decision.intent.value,
            )
            return route_to_chat(state)

        # Sistema multi-nivel para Vulnerabilidad
        if decision.intent == IntentType.VULNERABILITY:
            return self._handle_vulnerability_routing(state, decision)

        # Routing normal para otros intents
        return self._route_to_specialist(state, decision)

    def _handle_vulnerability_routing(
        self, state: GraphStateV2, decision: RoutingDecision
    ) -> str:
        """Maneja routing de vulnerabilidad con 3 niveles de confianza."""
        confidence = decision.confidence

        # Nivel 1: Alta confianza (>85%) → TCC directo
        if confidence >= MODERATE_CONFIDENCE_THRESHOLD:
            logger.info(
                f"Vulnerabilidad detectada con alta confianza ({confidence:.2f}). "
                f"Routing directo a cbt_specialist."
            )
            decision.next_actions = [
                "depth_empathy",
                "active_listening",
                "pacing_one_step",
            ]
            return self._route_to_specialist(state, decision)

        # Nivel 2: Confianza moderada (60-85%) → Clarificar
        if confidence >= LOW_CONFIDENCE_THRESHOLD:
            logger.info(
                f"Posible vulnerabilidad ({confidence:.2f}). "
                f"Añadiendo acción de clarificación."
            )
            decision.next_actions = [
                "clarify_emotional_state",
                "gentle_probe",
                "pacing_one_step",
            ]
            # Aún va a CBT, pero con instrucción de clarificar primero
            return self._route_to_specialist(state, decision)

        # Nivel 3: Baja confianza (50-60%) → Chat general
        logger.info(
            f"Señal débil de vulnerabilidad ({confidence:.2f}). "
            f"Routing a chat_specialist para evaluación suave."
        )
        decision.target_specialist = "chat_specialist"
        decision.next_actions = ["monitor_emotional_cues"]
        return self._route_to_specialist(state, decision)

    def _route_to_specialist(
        self, state: GraphStateV2, decision: RoutingDecision
    ) -> str:
        """Ejecuta el routing final a un especialista validado."""
        specialist_map = self._cache.get_tool_to_specialist_map()

        if decision.target_specialist in specialist_map.values():
            # Actualizar state y enrutar
            update_state_with_decision(state, decision)
            return decision.target_specialist
        logger.warning(f"Specialist '{decision.target_specialist}' no disponible")
        return route_to_chat(state)
