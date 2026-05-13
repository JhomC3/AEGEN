# src/personality/skill_parser.py
from __future__ import annotations

import logging
import re

import yaml

from src.core.schemas.skills import SkillContent, SkillManifest

logger = logging.getLogger(__name__)

# Regex para extraer el YAML frontmatter entre líneas '---'
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)

# Regex para extraer secciones Markdown iniciadas por '## '
_SECTION_RE = re.compile(r"^## (.+?)$\n(.*?)(?=^## |\Z)", re.MULTILINE | re.DOTALL)

# Mapeo de encabezados a campos del modelo SkillContent
_SECTION_MAP = {
    "tone modifiers": "tone_modifiers",
    "instructions": "instructions",
    "anti-patterns": "anti_patterns",
    "anti-patterns específicos": "anti_patterns",
    "reglas lingüísticas del skill": "linguistic_rules",
    "reglas linguisticas del skill": "linguistic_rules",
}


def parse_skill_md(content: str) -> SkillContent:
    """
    Parsea un archivo SKILL.md completo.
    Extrae el frontmatter YAML para el manifest y el body para las secciones Markdown.
    """
    manifest = _parse_frontmatter(content)
    sections = _parse_sections(content)

    known: dict[str, str] = {}
    raw: dict[str, str] = {}

    for heading, body in sections.items():
        key = _SECTION_MAP.get(heading.lower().strip())
        if key:
            # Si el encabezado mapea a un campo conocido, lo guardamos ahí
            known[key] = body.strip()
        else:
            # Si no, lo guardamos en raw_sections para no perder información
            raw[heading] = body.strip()

    return SkillContent(manifest=manifest, raw_sections=raw, **known)


def _parse_frontmatter(content: str) -> SkillManifest:
    """Extrae y parsea el YAML del frontmatter."""
    match = _FRONTMATTER_RE.match(content)
    if not match:
        return SkillManifest(name="Unknown", id="unknown")
    try:
        data = yaml.safe_load(match.group(1)) or {}
        return SkillManifest(**data)
    except Exception:
        logger.warning("Invalid YAML frontmatter in SKILL.md, using defaults")
        return SkillManifest(name="Unknown", id="unknown")


def _parse_sections(content: str) -> dict[str, str]:
    """Extrae las secciones Markdown del cuerpo del archivo."""
    # Eliminamos el frontmatter antes de buscar secciones
    body = _FRONTMATTER_RE.sub("", content)
    return {m.group(1): m.group(2) for m in _SECTION_RE.finditer(body)}
