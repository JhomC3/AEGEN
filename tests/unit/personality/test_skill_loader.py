from pathlib import Path

import pytest

from src.personality.skill_loader import SkillLoader


@pytest.mark.asyncio
async def test_skill_loader_discovers_skills() -> None:
    # El loader busca en src/personality/skills por defecto
    loader = SkillLoader()
    skills = await loader.discover_and_load()

    # Debería haber encontrado al menos chat, tcc y transcription (migrados en Fase 2)
    ids = [s.content.manifest.id for s in skills]
    assert "chat_specialist" in ids
    assert "cbt_specialist" in ids
    assert "transcription_agent" in ids


@pytest.mark.asyncio
async def test_skill_loader_loads_manifest_correctmente() -> None:
    loader = SkillLoader()
    skills = await loader.discover_and_load()

    chat_skill = next(s for s in skills if s.content.manifest.id == "chat_specialist")
    assert chat_skill.content.manifest.name == "MAGI Chat"
    assert "text" in chat_skill.content.manifest.capabilities
    assert chat_skill.content.manifest.requirements.update_history is True


@pytest.mark.asyncio
async def test_skill_loader_ignores_invalid_dirs(tmp_path: Path) -> None:
    # Crear un directorio sin SKILL.md
    invalid_skill = tmp_path / "invalid_skill"
    invalid_skill.mkdir()
    (invalid_skill / "some_file.txt").write_text("hello")

    loader = SkillLoader(skill_dirs=[tmp_path])
    skills = await loader.discover_and_load()
    assert len(skills) == 0


@pytest.mark.asyncio
async def test_skill_loader_loads_valid_skill(tmp_path: Path) -> None:
    # Crear un skill válido en directorio temporal
    skill_dir = tmp_path / "test_skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("""---
name: "Test"
id: "test_id"
version: "1.0.0"
capabilities: ["test"]
---
## Instructions
Test.
""")

    loader = SkillLoader(skill_dirs=[tmp_path])
    skills = await loader.discover_and_load()
    assert len(skills) == 1
    assert skills[0].content.manifest.id == "test_id"
