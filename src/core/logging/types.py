from typing import Any, TypeAlias

# --- Tipos para JSON ---
JsonValue: TypeAlias = str | int | float | bool | None | list[Any] | dict[str, Any]
JsonDict: TypeAlias = dict[str, "JsonValue"]
