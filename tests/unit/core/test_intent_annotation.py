"""Tests de anotación de intent en routing_tools."""

from src.core.routing_models import IntentType


def test_routing_tools_uses_intent_type_directly() -> None:
    """
    El parámetro 'intent' de route_user_message debe usar IntentType
    como tipo, no un Literal hardcodeado.

    Usar IntentType directamente elimina la fuente del bug BUG-3:
    no hay un segundo lugar que actualizar al añadir un nuevo intent.
    LangChain extrae los valores del enum automáticamente.
    """
    from src.agents.orchestrator.routing.routing_tools import route_user_message

    intent_schema = route_user_message.args.get("intent", {})
    ref = intent_schema.get("$ref", "")
    is_intent_type = "IntentType" in ref

    assert is_intent_type, (
        f"Se esperaba referencia a IntentType, pero se encontro {intent_schema}. "
        "Usar IntentType directamente evita la desincronizacion manual del Literal."
    )


def test_all_intent_type_values_are_valid() -> None:
    """
    Verifica que IntentType tenga al menos los valores esperados.
    Si este test falla tras añadir un valor, el cambio es legitimo.
    Si falla tras eliminar un valor, alguien rompio el enum.
    """
    values = {e.value for e in IntentType}
    assert "chat" in values
    assert "psicotrading" in values
    assert len(values) >= 11
