import logging
from typing import Any

from src.core.localization import get_country_info, resolve_localization

logger = logging.getLogger(__name__)


def update_localization_passive(
    profile: dict[str, Any], language_code: str | None
) -> bool:
    """
    C.9: Actualiza la información de localización en el perfil (Pasivo).
    Retorna True si el perfil fue modificado.
    """
    if not language_code:
        return False

    loc = profile.get("localization", {})

    # Si ya fue confirmado por el usuario, no sobrescribimos con data pasiva
    if loc.get("confirmed_by_user"):
        return False

    # Solo actualizar si es nuevo o diferente
    if loc.get("language_code") == language_code:
        return False

    # Resolver nueva localización
    new_loc = resolve_localization(language_code)
    new_loc["language_code"] = language_code
    new_loc["confirmed_by_user"] = False

    profile["localization"] = new_loc
    return True


def update_location_from_user_input(
    profile: dict[str, Any], country_code: str, region: str | None = None
) -> bool:
    """
    Actualiza localización basada en entrada explícita del usuario.
    Retorna True si el perfil fue modificado (siempre True si country válido).
    """
    loc = profile.get("localization", {})

    country_info = get_country_info(country_code)
    if not country_info:
        logger.warning(f"País no soportado: {country_code}")
        return False

    loc["country_code"] = country_code.upper()
    loc["confirmed_by_user"] = True

    if region and region.lower() in country_info["regions"]:
        reg_info = country_info["regions"][region.lower()]
        loc["region"] = region.lower()
        loc["dialect_hint"] = reg_info["dialect_hint"]
        loc["timezone"] = reg_info["timezone"]
    else:
        loc["region"] = None
        loc["dialect_hint"] = None
        loc["timezone"] = country_info["timezone"]

    loc["dialect"] = country_info["dialect"]

    profile["localization"] = loc
    return True
