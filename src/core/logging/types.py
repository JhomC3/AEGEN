from typing import Any, TypeAlias

# --- Tipos para JSON ---
JsonValue: TypeAlias = str | int | float | bool | None | list[Any] | dict[str, Any]  # noqa: UP040
JsonDict: TypeAlias = dict[str, "JsonValue"]  # noqa: UP040

# --- Tipos para Logging ---
LoggersConfig: TypeAlias = dict[str, dict[str, Any]]  # noqa: UP040
LoggingDictConfiguration: TypeAlias = dict[str, Any]  # noqa: UP040
