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

    # --- Adaptación de Personalidad ---
    if "personality_adaptation" in evo:
        pa_evo = evo["personality_adaptation"]
        pa = profile.get("personality_adaptation", {})

        # Estilo preferido
        if pa_evo.get("preferred_style"):
            pa["preferred_style"] = pa_evo["preferred_style"]
            updated = True

        # Ajuste de niveles (clamping entre 0 y 1)
        pa["humor_tolerance"] = max(
            0.0,
            min(
                1.0,
                pa.get("humor_tolerance", 0.7)
                + pa_evo.get("humor_tolerance_delta", 0.0),
            ),
        )
        pa["formality_level"] = max(
            0.0,
            min(
                1.0,
                pa.get("formality_level", 0.3)
                + pa_evo.get("formality_level_delta", 0.0),
            ),
        )

        # Nuevas preferencias
        if pa_evo.get("new_preferences"):
            pa["learned_preferences"] = list(
                set(pa.get("learned_preferences", []) + pa_evo["new_preferences"])
            )
            updated = True

        profile["personality_adaptation"] = pa

    if updated:
        await user_profile_manager.save_profile(chat_id, profile)
        logger.info(f"Perfil evolucionado (y personalidad adaptada) para {chat_id}")
