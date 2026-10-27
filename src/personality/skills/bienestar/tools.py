"""Herramienta del subagente de bienestar (fusión SDD 001).

Consultas y escrituras contra el proceso de dominio por HTTP loopback.
Auth: allowlist de chats antes de cualquier acceso; token solo en headers,
nunca en respuestas ni logs. Consultas nunca escriben; escrituras exigen
preview + confirmación con hash vinculado a chat, operación y datos.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.tools import tool

from src.core.config import settings
from src.personality.skills.bienestar import bienestar_ops as ops
from src.personality.skills.bienestar.confirms import _confirmar
from src.personality.skills.bienestar.domain_http import (
    _autorizado,
    _err,
    _get,
    _guardar_pendiente,
    _pide_confirmacion,
    _token,
)
from src.personality.skills.bienestar.previews import _preview_escritura
from src.personality.skills.bienestar.queries import _consulta

logger = logging.getLogger(__name__)


async def _preview_undo(chat_id: str) -> str:
    peek = await _get("/api/v1/undo/peek")
    e = _err(peek)
    if e:
        return e
    if peek.get("kind") == "empty" or not isinstance(peek.get("entry_id"), int):
        return "No hay nada que deshacer."
    hh = _guardar_pendiente(
        chat_id, "undo", {"expected": {"id": peek["entry_id"], "kind": peek["kind"]}}
    )
    detalle = f" del {peek['fecha_iso']}" if peek.get("fecha_iso") else ""
    return _pide_confirmacion(
        f"Voy a deshacer lo último ({peek.get('kind')}{detalle}, "
        f"entrada #{peek['entry_id']}).",
        hh,
    )


async def _ruta(
    user_message: str, chat_id: str, v: str, dom: str | None, tz: str
) -> str:
    if v == "undo":
        return await _preview_undo(chat_id)
    if v == "escritura" and dom:
        return await _preview_escritura(user_message, dom, chat_id, tz)
    if v == "consulta" and dom:
        return await _consulta(user_message, dom, tz)
    if dom:
        return (
            "¿Quieres consultar o registrar? Dime la fecha («hoy», «ayer» "
            "o 2026-10-04) y los datos."
        )
    return (
        "Puedo consultar y registrar entrenamiento, alimentación, "
        "respiración, cardio y Rumbo. Dime qué necesitas y para qué fecha."
    )


@tool
async def bienestar_tool(
    user_message: str,
    chat_id: str,
    conversation_history: list[dict[str, Any]] | None = None,
    routing_metadata: dict[str, Any] | None = None,
    rag_context: dict[str, Any] | None = None,
) -> str:
    """Consulta y gestiona el dominio de bienestar con autorización y confirmación."""
    tz = settings.BIENESTAR_TZ or "America/Bogota"
    if not _autorizado(chat_id):
        logger.warning("bienestar: chat no autorizado")
        return (
            "Este dominio es privado del dueño. Si eres él, configura tu "
            "chat como autorizado."
        )
    if _token() is None:
        return "El dominio no tiene credencial configurada."
    meta = routing_metadata or {}
    h = ops.extraer_hash_confirmacion(user_message) or meta.get("confirm_hash")
    if h:
        return await _confirmar(user_message, chat_id, h, tz)
    v = ops.verbo(user_message)
    dom = ops.dominio(user_message)
    if dom == "plantilla":
        from src.personality.skills.bienestar.previews_extra import _p_plantilla

        fecha = ops.resolver_fecha(user_message, tz) or ops.hoy_iso(tz)
        return await _p_plantilla(user_message, chat_id, fecha)
    return await _ruta(user_message, chat_id, v, dom, tz)


SKILL_TOOL = bienestar_tool
