# src/personality/skill_workshop.py
"""
Skill Workshop — Auto-creacion de skills por MAGI.

Permite a MAGI generar nuevos SKILL.md basandose en patrones
de interaccion observados. Los skills generados quedan en estado
'draft' y requieren aprobacion humana via Telegram.
"""

import logging
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger(__name__)

SKILL_WORKSHOP_PROMPT = """
Eres un experto disenador de skills para un asistente de IA.

Basandote en el siguiente patron de interaccion observado, genera
un SKILL.md completo con frontmatter YAML y secciones Markdown.

PATRON OBSERVADO:
{pattern}

EJEMPLOS DE INTERACCION:
{examples}

Genera el SKILL.md con la siguiente estructura:
---
name: "Nombre del Skill"
id: "{skill_id}"
version: "1.0.0"
status: "draft"
generated_by: "skill_workshop"
generated_at: "{generated_at}"
capabilities: ["cap1", "cap2"]
requires:
  env: []
  python_packages: []
  bins: []
priority: 6
---

## Propósito
[Descripcion del patron detectado]

## Instructions
[Protocolo especifico generado por el LLM]

## Anti-Patterns
[Lo que NO debe hacer este skill]

## Reglas Lingüisticas del Skill
[Estilo de comunicacion especifico]

Responde SOLO con el contenido del SKILL.md, sin explicaciones adicionales.
"""


async def generate_skill_from_pattern(
    pattern_description: str,
    example_interactions: list[dict],
    skill_id: str,
    output_dir: Path | None = None,
) -> Path:
    """
    Usa el LLM analitico para generar un SKILL.md completo
    a partir de un patron de interaccion observado.

    Args:
        pattern_description: Descripcion del patron detectado.
        example_interactions: Lista de interacciones de ejemplo.
        skill_id: ID unico para el skill.
        output_dir: Directorio de salida (default: storage/skills/user/).

    Returns:
        Path al archivo SKILL.md generado.
    """
    from src.core.engine import get_analytical_llm

    if output_dir is None:
        output_dir = Path("storage/skills/user")

    examples_text = "\n".join([
        f"- {e.get('role', 'user')}: {e.get('content', '')}"
        for e in example_interactions[:10]
    ])

    generated_at = datetime.now(UTC).isoformat()

    prompt = SKILL_WORKSHOP_PROMPT.format(
        pattern=pattern_description,
        examples=examples_text,
        skill_id=skill_id,
        generated_at=generated_at,
    )

    llm = get_analytical_llm()
    response = await llm.ainvoke(prompt)
    skill_content = response.content if hasattr(response, "content") else str(response)

    from src.personality.skill_parser import parse_skill_md

    parsed = parse_skill_md(skill_content)
    parsed.manifest.id = skill_id

    output_path = output_dir / skill_id / "SKILL.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(skill_content, encoding="utf-8")

    logger.info(
        "[SKILL-WORKSHOP] Skill generado: %s (status=draft)",
        skill_id,
    )
    return output_path


async def approve_skill(skill_id: str, skills_dir: Path | None = None) -> bool:
    """
    Aprueba un skill en estado draft, cambiandolo a active.

    Args:
        skill_id: ID del skill a aprobar.
        skills_dir: Directorio base de skills.

    Returns:
        True si se aprobo exitosamente.
    """
    if skills_dir is None:
        skills_dir = Path("storage/skills/user")

    skill_md = skills_dir / skill_id / "SKILL.md"
    if not skill_md.exists():
        logger.warning("[SKILL-WORKSHOP] Skill no encontrado: %s", skill_id)
        return False

    content = skill_md.read_text(encoding="utf-8")

    new_content = content.replace('status: "draft"', 'status: "active"')

    if new_content == content:
        logger.warning("[SKILL-WORKSHOP] Skill %s no tiene status draft", skill_id)
        return False

    skill_md.write_text(new_content, encoding="utf-8")
    logger.info("[SKILL-WORKSHOP] Skill aprobado: %s", skill_id)
    return True


async def reject_skill(skill_id: str, skills_dir: Path | None = None) -> bool:
    """
    Rechaza un skill en estado draft, moviendolo a .rejected/.

    Args:
        skill_id: ID del skill a rechazar.
        skills_dir: Directorio base de skills.

    Returns:
        True si se rechazo exitosamente.
    """
    import shutil

    if skills_dir is None:
        skills_dir = Path("storage/skills/user")

    skill_dir = skills_dir / skill_id
    if not skill_dir.exists():
        logger.warning("[SKILL-WORKSHOP] Skill no encontrado: %s", skill_id)
        return False

    rejected_dir = skills_dir / ".rejected"
    rejected_dir.mkdir(parents=True, exist_ok=True)

    target = rejected_dir / skill_id
    shutil.move(str(skill_dir), str(target))
    logger.info("[SKILL-WORKSHOP] Skill rechazado: %s", skill_id)
    return True
