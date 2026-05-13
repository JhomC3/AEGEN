import pytest

from src.personality.loader import PersonalityLoader


@pytest.mark.asyncio
async def test_load_skill_from_directory() -> None:
    # El loader usa src/personality/ como base por defecto
    loader = PersonalityLoader()

    # Probar carga de chat (nuevo formato)
    chat_skill = await loader.load_skill("chat")
    assert chat_skill is not None
    assert chat_skill.name == "MAGI Chat"
    assert chat_skill.linguistic_rules is not None
    assert "dialecto del usuario" in chat_skill.linguistic_rules


@pytest.mark.asyncio
async def test_load_skill_fallback_to_chat() -> None:
    loader = PersonalityLoader()

    # Probar carga de un skill inexistente -> debe retornar chat
    unknown_skill = await loader.load_skill("non_existent")
    assert unknown_skill is not None
    assert unknown_skill.name == "MAGI Chat"


@pytest.mark.asyncio
async def test_load_skill_tcc() -> None:
    loader = PersonalityLoader()

    # Probar carga de tcc (nuevo formato)
    tcc_skill = await loader.load_skill("tcc")
    assert tcc_skill is not None
    assert tcc_skill.name == "CBT Specialist"
    assert "distorsiones cognitivas" in tcc_skill.instructions
