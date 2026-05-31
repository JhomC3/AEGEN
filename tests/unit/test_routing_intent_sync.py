"""Valida que routing_tools usa IntentType directamente (ADR-0034)."""

from src.core.routing_models import IntentType


class TestIntentSynchronization:
    """Asegura que el tool del router usa IntentType como unica fuente de verdad."""

    def test_routing_uses_intent_type_directly(self):
        """Valida que intent referencia a IntentType, no a Literal."""
        from src.agents.orchestrator.routing.routing_tools import (
            route_user_message,
        )

        intent_schema = route_user_message.args.get("intent", {})
        ref = intent_schema.get("$ref", "")

        assert "IntentType" in ref, (
            f"Se esperaba IntentType, pero se encontro {intent_schema}. "
            "ADR-0034: usar IntentType directamente elimina la "
            "desincronizacion."
        )

    def test_all_intent_values_available(self):
        """Verifica que todos los valores de IntentType existen."""
        values = {e.value for e in IntentType}
        assert (
            "vulnerability" in values
        ), "CRITICO: 'vulnerability' no esta en IntentType"
        assert "topic_shift" in values, "CRITICO: 'topic_shift' no esta en IntentType"
        assert "psicotrading" in values, "CRITICO: 'psicotrading' no esta en IntentType"
        count = len(values)
        assert count >= 11, f"Se esperaban >=11 intents, se encontraron {count}"
