"""Tests de gating condicional de skills."""

from unittest.mock import patch

from src.personality.skill_loader import _check_requirements


def test_skill_loads_when_no_requires() -> None:
    """Un skill sin seccion `requires` siempre se carga."""
    assert _check_requirements({}) is True


def test_skill_blocked_when_env_missing() -> None:
    """Un skill con `requires.env` no se carga si la variable no esta configurada."""
    import os

    os.environ.pop("NONEXISTENT_API_KEY_XYZ", None)
    result = _check_requirements({"env": ["NONEXISTENT_API_KEY_XYZ"]})
    assert result is False


def test_skill_loads_when_env_present() -> None:
    """Un skill con `requires.env` se carga si la variable esta configurada."""
    with patch.dict("os.environ", {"MY_TEST_KEY": "some_value"}):
        result = _check_requirements({"env": ["MY_TEST_KEY"]})
    assert result is True


def test_skill_blocked_when_package_missing() -> None:
    """Un skill con `requires.python_packages` no se carga si el paquete no existe."""
    result = _check_requirements({"python_packages": ["nonexistent_package_xyz_abc"]})
    assert result is False


def test_skill_loads_when_package_present() -> None:
    """Un skill con `requires.python_packages` se carga si el paquete existe."""
    result = _check_requirements({"python_packages": ["json"]})
    assert result is True
