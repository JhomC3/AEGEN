# tests/unit/core/test_skill_manifest.py
import pytest
from pydantic import ValidationError

from src.core.schemas.skills import SkillContent, SkillManifest, SkillRequirements


def test_skill_manifest_minimal() -> None:
    m = SkillManifest(
        name="Test", id="test_skill", version="1.0.0", capabilities=["text"]
    )
    assert m.name == "Test"
    assert m.requirements.memory_access == "full"  # default
    assert m.requirements.priority == 5  # default
    assert m.requirements.update_history is True  # default
    assert m.requirements.chain_to is None  # default
    assert m.async_capable is False  # default


def test_skill_manifest_full() -> None:
    m = SkillManifest(
        name="CBT Specialist",
        id="cbt_therapeutic",
        version="1.0.0",
        capabilities=["psicologia", "tcc", "apoyo_emocional"],
        requirements=SkillRequirements(
            tools=["cbt_therapeutic_guidance_tool"],
            memory_access="full",
            priority=10,
            update_history=False,
            chain_to=None,
        ),
        async_capable=False,
    )
    assert m.requirements.priority == 10
    assert "tcc" in m.capabilities


def test_skill_manifest_rejects_empty_id() -> None:
    with pytest.raises(ValidationError):
        SkillManifest(name="X", id="", version="1.0.0", capabilities=[])


def test_skill_content_with_sections() -> None:
    sc = SkillContent(
        manifest=SkillManifest(name="T", id="t", version="1.0.0", capabilities=[]),
        tone_modifiers="Directo, eficiente",
        instructions="Responde conciso",
        anti_patterns="No uses jerga",
        linguistic_rules="Eco léxico activo",
    )
    assert sc.tone_modifiers == "Directo, eficiente"
    assert sc.linguistic_rules == "Eco léxico activo"
