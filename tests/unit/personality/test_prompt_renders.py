from src.personality.prompt_renders import render_dialect_rules, render_style_adaptation
from src.personality.types import LinguisticProfile, StyleSignals


def test_render_dialect_preferred_wins() -> None:
    lp = LinguisticProfile(
        dialect="colombiano",
        dialect_hint="paisa",
        preferred_dialect="argentino",
        dialect_confirmed=True,
        formality_level=0.3,
        humor_tolerance=0.7,
        preferred_style="casual",
    )
    result = render_dialect_rules(lp)
    assert "argentino" in result.lower()
    assert "Dialecto ACTIVO" in result
    assert "colombiano" not in result.lower()


def test_render_dialect_confirmed_location() -> None:
    lp = LinguisticProfile(
        dialect="mexicano",
        dialect_hint="chilango",
        preferred_dialect=None,
        dialect_confirmed=True,
        formality_level=0.3,
        humor_tolerance=0.7,
        preferred_style="casual",
    )
    result = render_dialect_rules(lp)
    assert "mexicano" in result.lower()
    assert "Contexto Regional" in result
    assert "modismos locales suaves" in result


def test_render_dialect_neutral_default() -> None:
    lp = LinguisticProfile(
        dialect="neutro",
        dialect_hint=None,
        preferred_dialect=None,
        dialect_confirmed=False,
        formality_level=0.3,
        humor_tolerance=0.7,
        preferred_style="casual",
    )
    result = render_dialect_rules(lp)
    assert "Neutralidad Cálida" in result
    assert "ECO LÉXICO" in result


def test_render_style_adaptation_none() -> None:
    assert render_style_adaptation(None) == ""


def test_render_style_muy_formal() -> None:
    style = StyleSignals(
        detected_language="es",
        formality_indicator="muy_formal",
        brevity="conciso",
        uses_emoji=True,
    )
    result = render_style_adaptation(style)
    assert "MUY FORMAL" in result
    assert "impecablemente profesional" in result


def test_render_style_casual() -> None:
    style = StyleSignals(
        detected_language="es",
        formality_indicator="casual",
        brevity="conciso",
        uses_emoji=True,
    )
    result = render_style_adaptation(style)
    assert "casual" in result.lower()
    assert "cercano y relajado" in result


def test_render_style_telegraphic() -> None:
    style = StyleSignals(
        detected_language="es",
        formality_indicator="casual",
        brevity="telegrafico",
        uses_emoji=True,
    )
    result = render_style_adaptation(style)
    assert "ULTRA-CONCISO" in result
    assert "directo al grano" in result


def test_render_style_no_emoji() -> None:
    style = StyleSignals(
        detected_language="es",
        formality_indicator="casual",
        brevity="conciso",
        uses_emoji=False,
    )
    result = render_style_adaptation(style)
    assert "NO usa emojis" in result
    assert "mínimo" in result
