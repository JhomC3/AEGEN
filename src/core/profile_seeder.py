import logging
from typing import Any, cast

logger = logging.getLogger(__name__)


def get_default_profile() -> dict[str, Any]:
    """Returns a complete default profile using the Pydantic model."""
    from src.core.schemas.profile import UserProfile

    return cast(dict[str, Any], UserProfile().model_dump())


def ensure_profile_complete(raw: dict[str, Any]) -> dict[str, Any]:
    """Validates and migrates an old profile dict."""
    from src.core.schemas.profile import UserProfile

    try:
        profile = UserProfile.model_validate(raw)
        profile.metadata.version = "1.2.0"
        return cast(dict[str, Any], profile.model_dump())
    except Exception as e:
        logger.warning("Profile migration failed: %s", e)
        defaults = get_default_profile()
        for key, value in raw.items():
            if (
                isinstance(value, dict)
                and key in defaults
                and isinstance(defaults[key], dict)
            ):
                defaults[key].update(value)
            else:
                defaults[key] = value
        return defaults
