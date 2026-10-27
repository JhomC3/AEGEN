"""Regresión: un fallo de herramienta debe marcar error en el estado (spec 002)."""

from types import SimpleNamespace
from typing import Any

import pytest

from src.agents.specialists.skill_based_specialist import SkillBasedSpecialist


class _ToolQueFalla:
    async def ainvoke(self, _args: dict[str, Any]) -> str:
        raise RuntimeError("proveedor caído")


class _Manifest:
    async_capable = False
    requirements = SimpleNamespace(update_history=False)


@pytest.mark.asyncio
async def test_fallo_de_herramienta_marca_error_message() -> None:
    specialist = SkillBasedSpecialist.__new__(SkillBasedSpecialist)
    attrs = vars(specialist)
    attrs["_name"] = "demo"
    attrs["_tool"] = _ToolQueFalla()
    attrs["_manifest"] = _Manifest()

    state: dict[str, Any] = {
        "payload": {},
        "event": SimpleNamespace(chat_id="123"),
    }

    response = await specialist._run_tool_logic(state, "hola")  # type: ignore[arg-type]

    assert "No pude" in response
    assert "problema técnico" not in response
    assert state["error_message"]
    assert "demo" in state["error_message"]
