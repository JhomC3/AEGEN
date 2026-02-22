# src/agents/orchestrator/routing/intent_parser.py
import logging
import re

logger = logging.getLogger(__name__)


def detect_explicit_command(text: str) -> str | None:
    """
    Detecta si el usuario está usando un comando explícito para activar
    un especialista. Ejemplos: /tcc, /terapeuta, /chat
    """
    text = text.strip().lower()

    commands = {
        "cbt_specialist": [r"^/tcc", r"^/terapeuta", r"^/psicologo"],
        "chat_specialist": [r"^/chat", r"^/magi"],
        # Futuros especialistas
        "coding_specialist": [r"^/coding", r"^/code", r"^/programar"],
    }

    for specialist, patterns in commands.items():
        if any(re.search(p, text) for p in patterns):
            return specialist

    return None


def is_conversational_only(text: str) -> bool:
    """
    Detecta si un mensaje es puramente conversacional (saludo/despedida)
    para evitar costo de LLM Router.
    """
    if detect_explicit_command(text):
        return False

    text = text.strip().lower()

    # Patrones de saludos simples y cortesía
    patterns = [
        r"^(hola|buenos\s*dias|buenas\s*tardes|buenas\s*noches|hey|hi|hello)[!.]*$",
        r"^(gracias|muchas\s*gracias|ok|vale|listo|entendido|grx|thx)[!.]*$",
        r"^(adios|chau|hasta\s*luego|nos\s*vemos|bye)[!.]*$",
        r"^(como\s*estas|que\s*tal|todo\s*bien)[?!.]*$",
    ]

    return bool(any(re.match(p, text) for p in patterns))
