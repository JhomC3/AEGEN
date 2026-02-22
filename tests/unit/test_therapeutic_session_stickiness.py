# tests/unit/test_therapeutic_session_stickiness.py
from unittest.mock import MagicMock

from src.agents.orchestrator.routing.therapeutic_session import (
    is_therapeutic_session_active,
    should_maintain_therapeutic_session,
)
from src.core.routing_models import IntentType, RoutingDecision


class TestTherapeuticStickiness:
    """Verifica que el router mantiene sesión CBT ante quejas."""

    def test_detects_active_therapeutic_session(self):
        """Si el último especialista fue CBT, la sesión terapéutica está activa."""
        state = {
            "event": MagicMock(event_type="text", content="no sirves"),
            "payload": {"last_specialist": "cbt_specialist"},
            "conversation_history": [],
        }
        assert is_therapeutic_session_active(state) is True

    def test_no_therapeutic_session_from_chat(self):
        state = {
            "event": MagicMock(event_type="text", content="hola"),
            "payload": {"last_specialist": "chat_specialist"},
            "conversation_history": [],
        }
        assert is_therapeutic_session_active(state) is False

    def test_complaint_during_cbt_stays_in_cbt(self):
        """Queja del usuario durante CBT = resistencia, no cambio de tema."""
        decision = RoutingDecision(
            intent=IntentType.CHAT,
            confidence=0.7,
            target_specialist="chat_specialist",
            requires_tools=False,
        )
        state = {
            "payload": {"last_specialist": "cbt_specialist"},
        }
        result = should_maintain_therapeutic_session(state, decision)
        assert result is True

    def test_explicit_topic_change_allowed(self):
        """Si el intent es TOPIC_SHIFT, sí se permite salir de CBT."""
        decision = RoutingDecision(
            intent=IntentType.TOPIC_SHIFT,
            confidence=0.9,
            target_specialist="chat_specialist",
            requires_tools=False,
        )
        state = {
            "payload": {"last_specialist": "cbt_specialist"},
        }
        result = should_maintain_therapeutic_session(state, decision)
        assert result is False
