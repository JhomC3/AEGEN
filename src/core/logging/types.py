from typing import Any, Literal, TypeAlias, TypedDict


class StandardTextFormatterConfig(TypedDict):
    format: str
    datefmt: str


# Para formateadores y manejadores que usan claves especiales como "()" o "class",
# la entrada correspondiente en el diccionario de configuración se tipará como dict[str, Any].
FormatterEntry = StandardTextFormatterConfig | dict[str, Any]  # Usando | para Union
FormattersConfig = dict[str, FormatterEntry]

HandlerEntry = dict[str, Any]  # Esto cubre ConsoleHandler y FileHandler
HandlersConfig = dict[str, HandlerEntry]


class LoggerConfig(TypedDict):
    level: str
    handlers: list[str]  # Usando list incorporada
    propagate: bool


LoggersConfig = dict[str, LoggerConfig]


class LoggingDictConfiguration(TypedDict, total=False):
    version: Literal[1]
    disable_existing_loggers: bool
    filters: dict[str, Any]
    formatters: FormattersConfig
    handlers: HandlersConfig
    loggers: LoggersConfig


# --- Tipos para JSON ---
JsonValue: TypeAlias = str | int | float | bool | None | list[Any] | dict[str, Any]
JsonDict: TypeAlias = dict[str, "JsonValue"]
