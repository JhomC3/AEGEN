"""
Módulo de configuración principal que maneja los diferentes entornos de la aplicación.
Provee una instancia global de configuración basada en el entorno actual.
"""

import logging

from .base import BaseAppSettings
from .development import DevAppSettings
from .environments import APP_ENV, Environment
from .production import ProdAppSettings

logger = logging.getLogger(__name__)

# Seleccionar la clase de settings correcta basada en el entorno
AppSettingsModel: type[BaseAppSettings] = (
    ProdAppSettings if APP_ENV == Environment.PRODUCTION else DevAppSettings
)

# Crear la instancia global de settings
settings: BaseAppSettings = AppSettingsModel()

# Log para verificar qué settings se cargaron
logger.info(f"Loaded settings for environment: {settings.APP_ENV.value}")
