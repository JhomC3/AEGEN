# tests/prompts/test_transcription_snapshot.py
from pathlib import Path
from typing import cast

import yaml


def load_prompt(prompt_name: str, version: str = "v1") -> str:
    """Carga el contenido de un prompt desde su archivo YAML."""
    prompt_path = (
        Path(__file__).parent.parent.parent
        / "prompts"
        / prompt_name
        / f"{version}.yaml"
    )
    if not prompt_path.exists():
        raise FileNotFoundError(
            f"El archivo de prompt no se encontró en: {prompt_path}"
        )
    with open(prompt_path, encoding="utf-8") as f:
        # Hacemos un cast explícito porque yaml.safe_load devuelve Any
        prompt_data = cast(dict[str, str], yaml.safe_load(f))
    return prompt_data["system_message"]


def test_transcription_agent_prompt_snapshot(snapshot):
    """
    Test de snapshot para el prompt del agente de transcripción.
    Compara el prompt actual con una versión guardada (snapshot).
    Si el prompt cambia, el test fallará hasta que el snapshot sea actualizado.
    """
    prompt_content = load_prompt("transcription_agent")
    snapshot.assert_match(prompt_content, "transcription_agent_v1.txt")
