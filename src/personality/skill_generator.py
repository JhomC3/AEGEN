"""Generador automático de skills basado en el historial (Learning Loop)."""

import logging
from pathlib import Path

from src.core.engine import llm

logger = logging.getLogger(__name__)

SKILL_GEN_PROMPT = """Eres el Arquitecto de Personalidad de AEGEN.
Tu tarea es sintetizar una nueva "Habilidad" (Skill) basada en un historial de
interacciones exitosas sobre un tema específico.

Analiza el historial proporcionado y genera un archivo SKILL.md que siga el estándar:
1. Un frontmatter YAML con: name, id, version (siempre 0.1.0-auto), capabilities.
2. Secciones Markdown: ## Tone Modifiers, ## Instructions, ## Anti-Patterns Específicos.

Reglas:
- El ID debe ser descriptivo (ej: nutrition_coach).
- Las instrucciones deben ser operativas, basadas en lo que funcionó.
- NO incluyas código Python.
- El tono debe ser coherente con MAGI pero adaptado al dominio.

Historial de referencia:
{history}

Genera solo el contenido del archivo SKILL.md:
"""


class SkillGenerator:
    """
    Analiza el conocimiento y las interacciones para proponer e instalar
    nuevos skills automáticamente.
    """

    def __init__(self, storage_path: str = "storage/skills") -> None:
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

    async def generate_from_history(
        self, domain_name: str, conversation_samples: list[str]
    ) -> str | None:
        """
        Genera un nuevo skill a partir de ejemplos de conversación.
        """
        logger.info("Iniciando generación de skill para el dominio: %s", domain_name)

        history_text = "\n---\n".join(conversation_samples)
        prompt = SKILL_GEN_PROMPT.format(history=history_text)

        try:
            response = await llm.ainvoke(prompt)
            content = str(response.content).strip()

            # Limpiar posibles bloques de código markdown del LLM
            if content.startswith("```"):
                content = "\n".join(content.split("\n")[1:-1])

            return content
        except Exception:
            logger.exception("Error invocando al LLM para generar skill")
            return None

    async def install_skill(self, content: str) -> bool:
        """
        Guarda el contenido de un skill en el almacenamiento de usuario.
        """
        from src.personality.skill_parser import parse_skill_md

        try:
            # Validar que el contenido es parseable antes de guardar
            parsed = parse_skill_md(content)
            skill_id = parsed.manifest.id

            skill_dir = self.storage_path / skill_id
            skill_dir.mkdir(exist_ok=True)

            skill_file = skill_dir / "SKILL.md"
            skill_file.write_text(content, encoding="utf-8")

            logger.info("Nuevo skill '%s' instalado en %s", skill_id, skill_file)
            return True
        except Exception:
            logger.exception("Error instalando nuevo skill dinámico")
            return False
