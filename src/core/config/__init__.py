"""Configuration module for AEGEN."""

from .base import BaseAppSettings
from .development import DevelopmentSettings
from .environments import APP_ENV, Environment
from .production import ProductionSettings


def get_settings() -> BaseAppSettings:
    """Factory function to get settings based on environment."""
    if APP_ENV == Environment.PRODUCTION:
        return ProductionSettings()
    if APP_ENV in [Environment.DEVELOPMENT, Environment.LOCAL]:
        return DevelopmentSettings()
    # Default to development settings
    return DevelopmentSettings()


# Create a global settings instance
settings = get_settings()
