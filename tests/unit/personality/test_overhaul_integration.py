import pytest

from src.personality.prompt_builder import system_prompt_builder


@pytest.mark.asyncio
async def test_prompt_adaptation_formal():
    profile = {
        "identity": {"name": "Carlos"},
        "personality_adaptation": {
            "preferred_style": "casual",
            "formality_level": 0.3,
            "humor_tolerance": 0.7,
        },
        "localization": {"dialect": "neutro", "confirmed_by_user": False},
    }

    # Mensajes muy formales
    messages = [
        "Estimado MAGI, le escribo para solicitar su asistencia.",
        "¿Podría usted informarme sobre el estado del proyecto?",
        "Agradezco de antemano su atención y quedo a la espera de su respuesta.",
    ]

    prompt = await system_prompt_builder.build(
        chat_id="test_formal", profile=profile, recent_user_messages=messages
    )

    # Verificar que el prompt contiene señales de formalidad
    assert "MUY FORMAL" in prompt
    assert "profesional" in prompt.lower()
    assert "Carlos" in prompt


@pytest.mark.asyncio
async def test_prompt_adaptation_casual_telegraphic():
    profile = {
        "identity": {"name": "Juan"},
        "personality_adaptation": {
            "preferred_style": "casual",
            "formality_level": 0.3,
            "humor_tolerance": 0.7,
        },
        "localization": {"dialect": "neutro", "confirmed_by_user": False},
    }

    # Mensajes casuales y cortos
    messages = ["hola q tal", "necesito ayuda xq no entiendo", "jaja ok pa"]

    prompt = await system_prompt_builder.build(
        chat_id="test_casual", profile=profile, recent_user_messages=messages
    )

    # Verificar que el prompt contiene señales casuales y concisas
    assert "casual" in prompt.lower()
    assert "ULTRA-CONCISO" in prompt
    assert "Juan" in prompt


@pytest.mark.asyncio
async def test_preferred_dialect_override():
    profile = {
        "identity": {"name": "Pedro"},
        "personality_adaptation": {"preferred_dialect": "argentino"},
        "localization": {"dialect": "colombiano", "confirmed_by_user": True},
    }

    prompt = await system_prompt_builder.build(chat_id="test_dialect", profile=profile)

    # El dialecto preferido debe ganar sobre el localizado
    assert "argentino" in prompt.lower()
    assert "colombiano" not in prompt.lower()
