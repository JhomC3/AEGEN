import os
from enum import Enum


class Environment(str, Enum):
    LOCAL = "local"
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "test"


APP_ENV = Environment(os.getenv("APP_ENV", "development").lower())
