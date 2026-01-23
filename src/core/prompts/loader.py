"""Sistema centralizado de carga de prompts para AEGEN."""

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# Ruta base calculada desde la raíz del paquete src
# Localización: src/core/prompts/loader.py -> src/
SRC_ROOT = Path(__file__).resolve().parent.parent.parent
PROMPTS_DIR = SRC_ROOT / "prompts"


@lru_cache(maxsize=32)
def load_text_prompt(filename: str) -> str:
    """
    Carga un prompt en formato texto (.txt).
    Usa lru_cache para evitar lecturas de disco repetitivas.
    """
    path = PROMPTS_DIR / filename

    # Intentar también en la raíz si no está en src (por compatibilidad legacy)
    legacy_path = SRC_ROOT.parent / "prompts" / filename

    potential_paths = [path, legacy_path]

    for p in potential_paths:
        if p.exists():
            try:
                content = p.read_text(encoding="utf-8")
                logger.debug(f"Prompt loaded successfully from: {p}")
                return content
            except Exception as e:
                logger.error(f"Error reading prompt file {p}: {e}")

    logger.error(
        f"Prompt file not found: {filename}. Looked in: {[str(p) for p in potential_paths]}"
    )
    return ""


@lru_cache(maxsize=16)
def load_yaml_prompt(agent_name: str, version: str = "v1") -> dict[str, Any]:
    """
    Carga un conjunto de prompts en formato YAML para un agente.
    """
    filename = f"{version}.yaml"
    path = PROMPTS_DIR / agent_name / filename

    # Legacy path check
    legacy_path = SRC_ROOT.parent / "prompts" / agent_name / filename

    potential_paths = [path, legacy_path]

    for p in potential_paths:
        if p.exists():
            try:
                with open(p, encoding="utf-8") as f:
                    content = yaml.safe_load(f)
                logger.debug(f"YAML prompts loaded successfully from: {p}")
                return content or {}
            except Exception as e:
                logger.error(f"Error parsing YAML prompt {p}: {e}")

    logger.error(
        f"YAML prompt file not found for {agent_name}. Looked in: {[str(p) for p in potential_paths]}"
    )
    return {}


def validate_required_prompts(required_list: list[str]) -> bool:
    """
    Valida la existencia de una lista de prompts críticos al inicio.
    Soporta rutas simples (txt) o carpetas (agentes yaml).
    """
    missing = []
    for item in required_list:
        path = PROMPTS_DIR / item
        if not path.exists():
            missing.append(item)

    if missing:
        logger.critical(f"CRITICAL: Missing required prompt files: {missing}")
        return False

    logger.info(f"All {len(required_list)} required prompts validated.")
    return True
