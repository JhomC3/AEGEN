# src/agents/utils/state_utils.py
from src.core.schemas import GraphStateV2


def extract_user_content_from_state(state: GraphStateV2) -> str | None:
    payload = state.get("payload", {})
    if payload.get("transcript"):
        return payload["transcript"]
    if state["event"].content:
        return str(state["event"].content)
    return None
