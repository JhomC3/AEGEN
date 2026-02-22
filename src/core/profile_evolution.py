from datetime import datetime
from typing import Any


def add_evolution_entry(
    profile: dict[str, Any], event: str, type: str = "milestone"
) -> None:
    """3.9: Registra cambios en el timeline y evolución."""
    now = datetime.now().isoformat()

    entry = {
        "date": now,
        "event": event,
        "type": type,
    }
    profile["timeline"].append(entry)
    profile["evolution"]["path_traveled"].append(entry)

    if type == "milestone":
        profile["evolution"]["milestones_count"] += 1
