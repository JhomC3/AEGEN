"""Test para create_observable_config — reproduce Bug 6 (AsyncCallbackManager)."""

from unittest.mock import MagicMock

from src.core.engine import create_observable_config


def test_create_observable_config_with_callback_manager() -> None:
    """Bug 6: config["callbacks"] puede ser un CallbackManager, no una lista."""
    fake_manager = MagicMock()
    fake_manager.__iter__ = MagicMock(side_effect=TypeError("not iterable"))
    fake_manager.handlers = []

    config: dict = {"callbacks": fake_manager}
    result = create_observable_config("chat_response", config)

    assert isinstance(result["callbacks"], list)
    assert len(result["callbacks"]) == 1
    assert result["callbacks"][0].__class__.__name__ == "LLMObservabilityHandler"


def test_create_observable_config_with_none_callbacks() -> None:
    """config["callbacks"] puede ser None."""
    config: dict = {"callbacks": None}
    result = create_observable_config("chat_response", config)
    assert isinstance(result["callbacks"], list)
    assert len(result["callbacks"]) == 1


def test_create_observable_config_with_list_callbacks() -> None:
    """Caso normal: callbacks es una lista."""
    config: dict = {"callbacks": []}
    result = create_observable_config("chat_response", config)
    assert isinstance(result["callbacks"], list)
    assert len(result["callbacks"]) == 1


def test_create_observable_config_no_config() -> None:
    """Sin config — debe crear uno nuevo."""
    result = create_observable_config("general")
    assert isinstance(result["callbacks"], list)
    assert len(result["callbacks"]) == 1
