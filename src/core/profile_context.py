from typing import Any, cast


def get_context_for_prompt(profile: dict[str, Any]) -> dict[str, str]:
    """Retorna contexto formateado desde el objeto perfil pasado."""
    psy = profile.get("psychological_state", {})
    val = profile.get("values_and_goals", {})

    metaphors = ", ".join(psy.get("key_metaphors", [])) or "None"
    struggles = ", ".join(psy.get("active_struggles", [])) or "None"
    values = ", ".join(val.get("core_values", [])) or "None"

    return {
        "phase": psy.get("current_phase", "Discovery"),
        "metaphors": metaphors,
        "struggles": struggles,
        "values": values,
        "goals": ", ".join(val.get("short_term_goals", [])) or "None",
    }


def get_active_tags(profile: dict[str, Any]) -> list[str]:
    return cast(list[str], profile.get("active_tags", []))


def get_style(profile: dict[str, Any]) -> str:
    return cast(str, profile.get("identity", {}).get("style", "Casual y Directo"))


def get_personality_adaptation(profile: dict[str, Any]) -> dict[str, Any]:
    """Retorna la configuración de adaptación de personalidad."""
    return cast(
        dict[str, Any],
        profile.get(
            "personality_adaptation",
            {
                "preferred_style": "casual",
                "communication_level": "intermediate",
                "humor_tolerance": 0.7,
                "formality_level": 0.3,
                "history_limit": 20,
                "learned_preferences": [],
            },
        ),
    )
