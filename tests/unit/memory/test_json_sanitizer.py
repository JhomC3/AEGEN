# tests/unit/memory/test_json_sanitizer.py
from src.memory.json_sanitizer import safe_json_loads


class TestSafeJsonLoads:
    """Verifica que JSON malformado se repara antes de fallar."""

    def test_valid_json_passes(self):
        result = safe_json_loads('{"name": "Jhonn"}')
        assert result == {"name": "Jhonn"}

    def test_single_quotes_repaired(self):
        """Causa raíz del Error A: comillas simples en SQLite."""
        result = safe_json_loads("{'name': 'Jhonn', 'age': 30}")
        assert result == {"name": "Jhonn", "age": 30}

    def test_trailing_comma_repaired(self):
        result = safe_json_loads('{"name": "Jhonn", "age": 30,}')
        assert result == {"name": "Jhonn", "age": 30}

    def test_completely_invalid_returns_none(self):
        result = safe_json_loads("esto no es JSON de ningún tipo")
        assert result is None

    def test_empty_string_returns_none(self):
        result = safe_json_loads("")
        assert result is None

    def test_none_input_returns_none(self):
        result = safe_json_loads(None)
        assert result is None

    def test_nested_single_quotes_repaired(self):
        raw = "{'identity': {'name': 'Jhonn'}, 'values': ['honestidad']}"
        result = safe_json_loads(raw)
        assert result["identity"]["name"] == "Jhonn"
        assert "honestidad" in result["values"]
