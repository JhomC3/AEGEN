# src/core/localization.py
"""
Base de datos de localización para AEGEN/MAGI.
Maneja mapeos de países a zonas horarias, dialectos y regiones.
"""

from typing import Any, TypedDict


class RegionInfo(TypedDict):
    dialect_hint: str
    timezone: str


class CountryInfo(TypedDict):
    name: str
    dialect: str
    timezone: str
    regions: dict[str, RegionInfo]


# Base de datos de países soportados con sus matices regionales
COUNTRY_DATA: dict[str, CountryInfo] = {
    "CO": {
        "name": "Colombia",
        "dialect": "colombiano",
        "timezone": "America/Bogota",
        "regions": {
            "bogota": {"dialect_hint": "rolo", "timezone": "America/Bogota"},
            "medellin": {"dialect_hint": "paisa", "timezone": "America/Bogota"},
            "cali": {"dialect_hint": "caleño", "timezone": "America/Bogota"},
            "barranquilla": {"dialect_hint": "costeño", "timezone": "America/Bogota"},
            "bucaramanga": {
                "dialect_hint": "santandereano",
                "timezone": "America/Bogota",
            },
            "pereira": {"dialect_hint": "paisa", "timezone": "America/Bogota"},
            "cartagena": {"dialect_hint": "costeño", "timezone": "America/Bogota"},
        },
    },
    "AR": {
        "name": "Argentina",
        "dialect": "argentino",
        "timezone": "America/Argentina/Buenos_Aires",
        "regions": {
            "buenos_aires": {
                "dialect_hint": "porteño",
                "timezone": "America/Argentina/Buenos_Aires",
            },
            "cordoba": {
                "dialect_hint": "cordobés",
                "timezone": "America/Argentina/Cordoba",
            },
            "rosario": {
                "dialect_hint": "santafesino",
                "timezone": "America/Argentina/Buenos_Aires",
            },
            "mendoza": {
                "dialect_hint": "mendocino",
                "timezone": "America/Argentina/Mendoza",
            },
        },
    },
    "MX": {
        "name": "México",
        "dialect": "mexicano",
        "timezone": "America/Mexico_City",
        "regions": {
            "cdmx": {"dialect_hint": "chilango", "timezone": "America/Mexico_City"},
            "monterrey": {"dialect_hint": "regio", "timezone": "America/Monterrey"},
            "guadalajara": {
                "dialect_hint": "tapatío",
                "timezone": "America/Mexico_City",
            },
        },
    },
    "ES": {
        "name": "España",
        "dialect": "español",
        "timezone": "Europe/Madrid",
        "regions": {
            "madrid": {"dialect_hint": "madrileño", "timezone": "Europe/Madrid"},
            "barcelona": {"dialect_hint": "catalán", "timezone": "Europe/Madrid"},
            "sevilla": {"dialect_hint": "andaluz", "timezone": "Europe/Madrid"},
            "bilbao": {"dialect_hint": "vasco", "timezone": "Europe/Madrid"},
        },
    },
}

# Mapeo de language_code (Telegram) a códigos de país ISO
LANGUAGE_TO_COUNTRY = {
    "es-co": "CO",
    "es-ar": "AR",
    "es-mx": "MX",
    "es-es": "ES",
    # Mapeos genéricos que requieren confirmación posterior o análisis
    "es": None,  # Español neutro por defecto
}


def get_country_info(country_code: str | None) -> CountryInfo | None:
    """Retorna información del país si existe en la base de datos."""
    if not country_code:
        return None
    return COUNTRY_DATA.get(country_code.upper())


def resolve_localization(language_code: str | None) -> dict[str, Any]:
    """
    Resuelve la localización inicial basada en el language_code.
    """
    if not language_code:
        return {
            "country_code": None,
            "timezone": "UTC",
            "dialect": "neutro",
            "dialect_hint": None,
        }

    normalized_code = language_code.lower()
    country_code = LANGUAGE_TO_COUNTRY.get(normalized_code)

    if country_code:
        info = COUNTRY_DATA[country_code]
        return {
            "country_code": country_code,
            "timezone": info["timezone"],
            "dialect": info["dialect"],
            "dialect_hint": None,
        }

    # Fallback para "es" o códigos no mapeados
    return {
        "country_code": None,
        "timezone": "UTC",
        "dialect": "neutro",
        "dialect_hint": None,
    }
