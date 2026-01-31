# src/core/profiling_manager.py
"""
Gestiona el perfilamiento proactivo de los usuarios de AEGEN/MAGI.
Identifica información faltante y sugiere preguntas naturales para el LLM.
"""

import logging
from typing import Any

from src.core.localization import COUNTRY_DATA, get_country_info
from src.core.profile_manager import user_profile_manager

logger = logging.getLogger(__name__)


class ProfilingManager:
    """
    Orquestador de preguntas de perfilamiento.
    """

    async def get_profiling_hint(self, profile: dict[str, Any]) -> str | None:
        """
        Determina si hay información crítica faltante y retorna un hint para el LLM.
        """
        loc = profile.get("localization", {})

        # 1. País no confirmado
        if not loc.get("confirmed_by_user") or not loc.get("country_code"):
            return (
                "Todavía no estamos seguros de su país/ubicación exacta. "
                "Si surge de forma natural, podrías preguntar '¿Desde dónde me escribes?' "
                "para ajustar mejor tu tono y zona horaria."
            )

        # 2. Región no especificada (solo para países con regiones mapeadas)
        country_code = loc.get("country_code")
        country_info = get_country_info(country_code)

        if country_info and country_info.get("regions") and not loc.get("region"):
            regions_list = ", ".join(list(country_info["regions"].keys())[:5])
            return (
                f"Sabemos que está en {country_info['name']}, pero no su ciudad/región. "
                "Si el tema sale, podrías preguntar en qué ciudad está. "
                f"(Ejemplos de regiones que conozco: {regions_list})"
            )

        return None

    async def process_potential_location_data(self, chat_id: str, text: str) -> bool:
        """
        Analiza el texto del usuario buscando confirmación de país o región.
        Retorna True si encontró y actualizó algo.
        """
        text_lower = text.lower()

        # 1. Buscar Países
        for code, info in COUNTRY_DATA.items():
            # Match exacto o nombre del país
            if info["name"].lower() in text_lower:
                # Verificar si menciona una región de ese país
                found_region = None
                for reg_id in info["regions"]:
                    if reg_id in text_lower:
                        found_region = reg_id
                        break

                await user_profile_manager.update_location_from_user_input(
                    chat_id, code, found_region
                )
                return True

        return False


# Singleton
profiling_manager = ProfilingManager()
