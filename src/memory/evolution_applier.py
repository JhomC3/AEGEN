import logging
from typing import Any

from src.core.profile_manager import user_profile_manager

logger = logging.getLogger(__name__)


async def apply_evolution(
    chat_id: str, profile: dict[str, Any], evo: dict[str, Any]
) -> None:
    """Aplica los cambios detectados al perfil."""
    updated = False

    if evo.get("milestone_detected"):
        await user_profile_manager.add_evolution_entry(
            chat_id, evo["milestone_detected"]
        )
        updated = True

    # Actualizar valores/metas si hay novedades
    if evo.get("new_values"):
        profile["values_and_goals"]["core_values"].extend(evo["new_values"])
        profile["values_and_goals"]["core_values"] = list(
            set(profile["values_and_goals"]["core_values"])
        )
        updated = True

    # Delegar adaptaciones complejas
    if _apply_personality_adaptation(profile, evo):
        updated = True

    if _apply_linguistic_adaptation(profile, evo):
        updated = True

    if updated:
        await user_profile_manager.save_profile(chat_id, profile)
        logger.info(f"Perfil evolucionado (y personalidad adaptada) para {chat_id}")


def _apply_personality_adaptation(profile: dict[str, Any], evo: dict[str, Any]) -> bool:
    """Aplica cambios en la personalidad detectados por el analista LLM."""
    if "personality_adaptation" not in evo:
        return False

    pa_evo = evo["personality_adaptation"]
    pa = profile.get("personality_adaptation", {})
    updated = False

    # Estilo preferido
    if pa_evo.get("preferred_style"):
        pa["preferred_style"] = pa_evo["preferred_style"]
        updated = True

    # Ajuste de niveles (clamping entre 0 y 1)
    pa["humor_tolerance"] = max(
        0.0,
        min(
            1.0,
            pa.get("humor_tolerance", 0.7) + pa_evo.get("humor_tolerance_delta", 0.0),
        ),
    )
    pa["formality_level"] = max(
        0.0,
        min(
            1.0,
            pa.get("formality_level", 0.3) + pa_evo.get("formality_level_delta", 0.0),
        ),
    )

    # Nuevas preferencias
    if pa_evo.get("new_preferences"):
        pa["learned_preferences"] = list(
            set(pa.get("learned_preferences", []) + pa_evo["new_preferences"])
        )
        updated = True

    profile["personality_adaptation"] = pa
    return updated


def _apply_linguistic_adaptation(profile: dict[str, Any], evo: dict[str, Any]) -> bool:
    """Aplica cambios en preferencias lingüísticas explícitas."""
    if "linguistic_preference" not in evo:
        return False

    lp = evo["linguistic_preference"]
    pa = profile.get("personality_adaptation", {})
    updated = False

    # Ajuste de formalidad (pasos de 0.15)
    if lp.get("prefers_more_formal"):
        pa["formality_level"] = min(1.0, pa.get("formality_level", 0.3) + 0.15)
        updated = True
    elif lp.get("prefers_more_casual"):
        pa["formality_level"] = max(0.0, pa.get("formality_level", 0.3) - 0.15)
        updated = True

    # Guardar solicitud de dialecto explícita
    if lp.get("explicit_dialect_request"):
        pa["preferred_dialect"] = lp["explicit_dialect_request"]
        updated = True

    # Guardar feedback como preferencia aprendida
    if lp.get("language_feedback"):
        pa.setdefault("learned_preferences", []).append(
            f"Feedback de tono: {lp['language_feedback']}"
        )
        pa["learned_preferences"] = list(set(pa["learned_preferences"]))
        updated = True

    profile["personality_adaptation"] = pa
    return updated
