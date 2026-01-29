"""Valida sincronización entre IntentType enum y routing_tools Literal."""

from src.core.routing_models import IntentType


class TestIntentSynchronization:
    """Asegura que todos los IntentType estén disponibles en el tool."""

    def test_all_intents_in_function_literal(self):
        """Valida que todos los IntentType estén en el Literal del tool."""
        from src.agents.orchestrator.routing.routing_tools import route_user_message

        # Obtener el schema del tool
        schema = route_user_message.args_schema.schema()
        literal_intents = set(schema["properties"]["intent"]["enum"])

        # Todos los IntentType
        enum_intents = {intent.value for intent in IntentType}

        missing = enum_intents - literal_intents
        extra = literal_intents - enum_intents

        assert not missing, f"Intents faltantes en routing_tools.py: {missing}"
        assert not extra, f"Intents extra en routing_tools.py no en enum: {extra}"

    def test_vulnerability_intent_exists(self):
        """Verifica específicamente que vulnerability esté sincronizado."""
        from src.agents.orchestrator.routing.routing_tools import route_user_message

        schema = route_user_message.args_schema.schema()
        literal_intents = schema["properties"]["intent"]["enum"]

        assert (
            "vulnerability" in literal_intents
        ), "CRÍTICO: 'vulnerability' no está en routing_tools.py"
        assert (
            "topic_shift" in literal_intents
        ), "CRÍTICO: 'topic_shift' no está en routing_tools.py"
