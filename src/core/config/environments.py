import os
from enum import Enum


class Environment(str, Enum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TESTING = "testing"


APP_ENV = Environment(os.getenv("APP_ENV", "dev").lower())
