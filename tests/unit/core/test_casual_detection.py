"""Tests de deteccion de mensajes casuales en context_retriever."""

import pytest

from src.agents.orchestrator.context_retriever import _is_casual_message


@pytest.mark.parametrize(
    "text,expected",
    [
        ("hola", True),
        ("hey", True),
        ("Hola!", True),
        ("buenas tardes", True),
        ("ok", True),
        ("gracias", True),
        ("bye", True),
        ("👋", True),
        ("entendido", True),
        ("si", False),
        ("no", False),
        ("¿como estoy?", False),
        ("Tengo ansiedad hoy", False),
        ("¿que deberia hacer con mi dieta?", False),
        ("ok, cuentame mas sobre TCC", False),
        ("estoy mal", False),
        ("me muero", False),
        ("ayuda", False),
    ],
)
def test_is_casual_message(text: str, expected: bool) -> None:
    assert _is_casual_message(text) == expected, f"Para '{text}' esperaba {expected}"
