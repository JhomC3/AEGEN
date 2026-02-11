# src/api/routers/privacy.py
"""
Comandos de control de privacidad del usuario.

Maneja /privacidad, /olvidar, /efimero antes del orquestador.
"""

from __future__ import annotations

import logging

from src.core.dependencies import get_sqlite_store, get_vector_memory_manager
from src.core.profile_manager import user_profile_manager

logger = logging.getLogger(__name__)

_PRIVACY_COMMANDS = frozenset({"/privacidad", "/olvidar", "/efimero", "/disclaimer"})


def is_privacy_command(text: str | None) -> bool:
    """Retorna True si el mensaje es un comando de privacidad."""
    if not text:
        return False
    return text.strip().split()[0].lower() in _PRIVACY_COMMANDS


async def handle_privacy_command(text: str, chat_id: str) -> str | None:
    """
    Procesa un comando de privacidad. Retorna el texto de respuesta,
    o None si no es un comando de privacidad.
    """
    parts = text.strip().split(maxsplit=1)
    command = parts[0].lower()
    arg = parts[1].strip() if len(parts) > 1 else ""

    if command == "/privacidad":
        return await _handle_privacidad(chat_id)
    elif command == "/olvidar":
        return await _handle_olvidar(chat_id, arg)
    elif command == "/efimero":
        return await _handle_efimero(chat_id)
    elif command == "/disclaimer":
        return _handle_disclaimer()

    return None


async def _handle_privacidad(chat_id: str) -> str:
    store = get_sqlite_store()
    stats = await store.get_memory_stats(chat_id)

    if stats["total"] == 0:
        return "No tengo datos almacenados sobre ti."

    lines = [f"Tengo {stats['total']} fragmentos de memoria sobre ti:\n"]
    for mtype, count in stats["by_type"].items():
        label = {
            "fact": "Hechos",
            "conversation": "Conversaciones",
            "preference": "Preferencias",
            "document": "Documentos",
        }.get(mtype, mtype)
        lines.append(f"  {label}: {count}")

    lines.append("\nPor sensibilidad:")
    for sens, count in stats["by_sensitivity"].items():
        label = {"low": "Baja", "medium": "Media", "high": "Alta"}.get(sens, sens)
        lines.append(f"  {label}: {count}")

    lines.append("\nComandos: /olvidar [tema] | /efimero | /disclaimer")
    return "\n".join(lines)


async def _handle_olvidar(chat_id: str, topic: str) -> str:
    if not topic:
        return "Uso: /olvidar [tema]\nEjemplo: /olvidar trabajo\n\nBuscaré y borraré memorias relacionadas con ese tema."

    vmm = get_vector_memory_manager()
    count = await vmm.delete_memories_by_query(user_id=chat_id, query=topic)

    if count == 0:
        return f"No encontré memorias relacionadas con '{topic}'."
    return f"Listo. Desactivé {count} memorias relacionadas con '{topic}'."


async def _handle_efimero(chat_id: str) -> str:
    profile = await user_profile_manager.load_profile(chat_id)
    ms = profile.get("memory_settings", {})
    current = ms.get("ephemeral_mode", False)
    ms["ephemeral_mode"] = not current
    profile["memory_settings"] = ms
    await user_profile_manager.save_profile(chat_id, profile)

    if not current:
        return "Modo efímero ACTIVADO. No guardaré nada de esta sesión. Usa /efimero de nuevo para desactivar."
    return "Modo efímero DESACTIVADO. Volveré a guardar memorias normalmente."


def _handle_disclaimer() -> str:
    return (
        "AEGEN es una herramienta experimental de acompañamiento basada en técnicas de "
        "Terapia Cognitivo Conductual (TCC). NO es un sustituto de atención profesional "
        "de salud mental.\n\n"
        "Si estás en crisis o necesitas ayuda urgente:\n"
        "- Línea 106 (Colombia)\n"
        "- Emergencias: 911\n\n"
        "Tus datos se almacenan localmente. Usa /privacidad para ver qué sé de ti, "
        "/olvidar para borrar datos, o /efimero para sesiones sin memoria."
    )
