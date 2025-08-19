# src/agents/specialists/planner/prompt_manager.py
"""
Gestión de prompts para PlannerAgent.
Encapsula carga, validación y acceso a prompts siguiendo Single Responsibility.
"""

import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# Path to prompts directory following project conventions
PROMPTS_DIR = (
    Path(__file__).parent.parent.parent.parent.parent / "prompts" / "planner_agent"
)


class PlannerPromptManager:
    """
    Maneja carga y acceso a prompts del PlannerAgent.
    Single responsibility: gestión de prompts.
    """

    def __init__(self, prompt_file: str = "v1.yaml"):
        self._prompt_file = PROMPTS_DIR / prompt_file
        self._prompts = self._load_prompts()

    def _load_prompts(self) -> dict[str, Any]:
        """Load prompts from YAML file with error handling."""
        try:
            with open(self._prompt_file, encoding="utf-8") as f:
                prompts = yaml.safe_load(f)

            if not prompts:
                raise ValueError("Prompt file is empty or invalid")

            return prompts

        except FileNotFoundError:
            logger.error(f"Prompt file not found: {self._prompt_file}")
            return self._get_fallback_prompts()
        except yaml.YAMLError as e:
            logger.error(f"YAML parsing error: {e}")
            return self._get_fallback_prompts()
        except Exception as e:
            logger.error(f"Unexpected error loading prompts: {e}")
            return self._get_fallback_prompts()

    def _get_fallback_prompts(self) -> dict[str, Any]:
        """Fallback prompts si no se puede cargar el archivo."""
        return {
            "system_message": "Eres un agente de planificación inteligente. Analiza el contexto y genera respuestas apropiadas.",
            "decision_prompt": "Analiza el contexto proporcionado y genera una respuesta conversacional apropiada.",
        }

    def get_system_message(self) -> str:
        """Get system message prompt."""
        return self._prompts.get("system_message", "Eres un asistente inteligente.")

    def get_decision_prompt(self) -> str:
        """Get decision making prompt."""
        return self._prompts.get(
            "decision_prompt", "Analiza y responde apropiadamente."
        )

    def get_prompt(self, key: str) -> str:
        """Get specific prompt by key with error handling."""
        prompt = self._prompts.get(key)
        if prompt is None:
            logger.warning(f"Prompt key '{key}' not found, returning empty string")
            return ""
        return str(prompt)

    def has_prompt(self, key: str) -> bool:
        """Check if prompt key exists."""
        return key in self._prompts


# Singleton instance for reuse across planner components
planner_prompts = PlannerPromptManager()
