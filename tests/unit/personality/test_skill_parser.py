# tests/unit/personality/test_skill_parser.py
from src.personality.skill_parser import parse_skill_md

VALID_SKILL_MD = """---
name: "CBT Specialist"
id: "cbt_therapeutic"
version: "1.0.0"
capabilities: ["psicologia", "tcc"]
requirements:
  tools: ["cbt_therapeutic_guidance_tool"]
  memory_access: "full"
  priority: 10
---
## Tone Modifiers
Empático analítico. Firmeza profesional.

## Instructions
Detecta distorsiones cognitivas.
Reestructuración agresiva.

## Anti-Patterns Específicos
No uses tono maternal.

## Reglas Lingüísticas del Skill
Firmeza benevolente.
"""


def test_parse_valid_skill_md() -> None:
    result = parse_skill_md(VALID_SKILL_MD)
    assert result.manifest.name == "CBT Specialist"
    assert result.manifest.id == "cbt_therapeutic"
    assert result.manifest.requirements.priority == 10
    assert "Empático" in result.tone_modifiers
    assert "distorsiones" in result.instructions
    assert "maternal" in result.anti_patterns
    assert "Firmeza benevolente" in result.linguistic_rules


def test_parse_missing_frontmatter() -> None:
    result = parse_skill_md("## Instructions\nHaz cosas.")
    assert result.manifest.id == "unknown"
    assert "Haz cosas" in result.instructions


def test_parse_empty_content() -> None:
    result = parse_skill_md("")
    assert result.manifest.id == "unknown"


def test_parse_invalid_yaml_graceful() -> None:
    content = "---\n[invalid yaml: {{\n---\n## Instructions\nFallback."
    result = parse_skill_md(content)
    assert result.manifest.id == "unknown"
    assert "Fallback" in result.instructions


def test_parse_extra_sections_preserved() -> None:
    content = "---\nname: X\nid: x\n---\n## Custom Section\nDatos custom."
    result = parse_skill_md(content)
    assert "Custom Section" in result.raw_sections
    assert "Datos custom" in result.raw_sections["Custom Section"]
