import logging
from typing import Any

from src.core.routing_models import EntityInfo, IntentType, RoutingDecision

logger = logging.getLogger(__name__)


def create_fallback_decision_data() -> dict[str, Any]:
    """
    Crea decision data fallback para casos de error.
    """
    return {
        "intent": "chat",
        "confidence": 0.3,
        "target_specialist": "chat_specialist",
        "requires_tools": False,
        "entities": [],
        "next_actions": [],
        "processing_metadata": {
            "fallback_reason": "Function call extraction failed",
            "method": "function_calling_fallback",
        },
    }


def extract_tool_result(response) -> dict[str, Any]:
    """
    Extrae resultado del function call y retorna data dict.
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
    return create_fallback_decision_data()


def build_routing_decision_from_data(decision_data: dict[str, Any]) -> RoutingDecision:
    """
    Construye RoutingDecision desde function call data.
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
                    confidence=0.8,
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


def create_fallback_decision(message: str) -> RoutingDecision:
    """
    Crea decisión fallback segura cuando falla análisis LLM.
    """
    return RoutingDecision(
        intent=IntentType.CHAT,
        confidence=0.5,
        target_specialist="chat_specialist",
        requires_tools=False,
        entities=[],
        subintent=None,
        next_actions=[],
        processing_metadata={
            "fallback_reason": "LLM analysis failed",
            "message_length": len(message),
            "method": "function_calling_fallback",
        },
    )
