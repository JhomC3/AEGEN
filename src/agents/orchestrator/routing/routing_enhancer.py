import logging

from src.agents.orchestrator.specialist_cache import SpecialistCache
from src.core.routing_models import IntentType, RoutingDecision

from .routing_patterns import IntentValidator, PatternExtractor, SpecialistMapper

logger = logging.getLogger(__name__)


class RoutingEnhancer:
    """
    Componente responsable de mejorar y validar las decisiones de enrutamiento.
    """

    def __init__(self) -> None:
        self.pattern_extractor = PatternExtractor()
        self.intent_validator = IntentValidator()
        self.specialist_mapper = SpecialistMapper()

    def enhance_decision(
        self, decision: RoutingDecision, message: str, cache: SpecialistCache
    ) -> RoutingDecision:
        """
        Mejora decisión LLM usando componentes especializados.
        """
        # Extraer entidades adicionales con pattern extractor
        pattern_entities = self.pattern_extractor.extract_entities_from_text(message)
        decision.entities.extend(pattern_entities)

        # Ajustar confianza si hay evidencia clara del intent
        if self.intent_validator.has_clear_intent_evidence(message, decision.intent):
            decision.confidence = min(decision.confidence + 0.15, 1.0)

        # Resolver nombre de tool a name de specialist
        tool_to_specialist = cache.get_tool_to_specialist_map()

        if decision.target_specialist in tool_to_specialist:
            resolved_specialist = tool_to_specialist[decision.target_specialist]
            logger.info(
                "Traduciendo target '%s' (tool) → '%s' (specialist)",
                decision.target_specialist,
                resolved_specialist,
            )
            decision.target_specialist = resolved_specialist

        # Validar que el especialista del LLM exista, sino usar fallback por intent
        available_specialists = list(tool_to_specialist.values())

        if decision.target_specialist not in available_specialists:
            logger.warning(
                f"LLM sugirió '{decision.target_specialist}' no disponible. "
                f"Mapeando por intent: {decision.intent.value}"
            )
            decision.target_specialist = (
                self.specialist_mapper.map_intent_to_specialist(decision.intent, cache)
            )

        # Determinar requirement de tools
        decision.requires_tools = decision.intent != IntentType.CHAT

        return decision
