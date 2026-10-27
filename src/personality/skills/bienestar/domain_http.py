"""HTTP y estado del dominio de bienestar (fusión SDD 001).

Auth por allowlist antes de acceder; token solo en headers. Las respuestas
200 se validan (`schema_version`); un error HTTP nunca se devuelve como datos.
Un timeout tras un POST es resultado incierto, nunca «nada se escribió».
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from src.core.config import settings
from src.personality.skills.bienestar import bienestar_ops as ops

logger = logging.getLogger(__name__)

_TIMEOUT = 10.0
_PENDIENTES: dict = {}
_ULTIMAS: dict = {}


def _autorizado(chat_id: str) -> bool:
    permitidos = list(settings.BIENESTAR_ALLOWED_CHAT_IDS)
    if settings.ADMIN_CHAT_ID and settings.ADMIN_CHAT_ID not in permitidos:
        permitidos.append(settings.ADMIN_CHAT_ID)
    return bool(chat_id) and chat_id in permitidos


def _base() -> str:
    return settings.BIENESTAR_DOMAIN_URL.rstrip("/")


def _token() -> str | None:
    raw = settings.BIENESTAR_SYNC_TOKEN
    return raw.get_secret_value() if raw else None


def _ok_versionada(r: httpx.Response) -> dict | None:
    """200 con JSON y `schema_version == 1`, o dict de error (nunca datos)."""
    try:
        data: dict = r.json()
    except ValueError:
        return {"_error": "formato", "_detail": "Respuesta incompatible del dominio."}
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        return {
            "_error": "formato",
            "_detail": "Versión de respuesta desconocida del dominio.",
        }
    return None


def _mapea_error(r: httpx.Response) -> dict:
    if r.status_code in (400, 404, 409, 413):
        try:
            detail = r.json().get("detail", "?")
        except ValueError:
            detail = "Datos rechazados por el dominio."
        return {"_error": "validacion", "_detail": detail}
    if r.status_code == 401:
        return {"_error": "auth", "_detail": "Credencial del dominio rechazada."}
    if r.status_code == 503:
        return {"_error": "config", "_detail": "Dominio sin credencial configurada."}
    if r.status_code >= 500:
        return {
            "_error": "servidor",
            "_detail": "El dominio devolvió un error interno.",
        }
    return {
        "_error": "formato",
        "_detail": f"Respuesta inesperada del dominio ({r.status_code}).",
    }


async def _get(path: str, params: dict | None = None) -> dict:
    token = _token()
    if not token:
        return {"_error": "config", "_detail": "Dominio sin credencial configurada."}
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as cli:
            r = await cli.get(
                _base() + path, headers={"X-Sync-Token": token}, params=params or {}
            )
    except (httpx.ConnectError, httpx.TimeoutException):
        return {
            "_error": "red",
            "_detail": "Dominio no disponible ahora mismo. "
            "Puedes usar la aplicación directa.",
        }
    if r.status_code != 200:
        return _mapea_error(r)
    return _ok_versionada(r) or r.json()


async def _post(path: str, payload: dict) -> dict:
    token = _token()
    if not token:
        return {"_error": "config", "_detail": "Dominio sin credencial configurada."}
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as cli:
            r = await cli.post(
                _base() + path, headers={"X-Sync-Token": token}, json=payload
            )
    except (httpx.ConnectError, httpx.TimeoutException):
        return {
            "_error": "incierto",
            "_detail": "No se sabe si se guardó: la respuesta se perdió. "
            "Revisa el día en la aplicación directa antes de reintentar; "
            "no reenvíes a ciegas.",
        }
    if r.status_code != 200:
        return _mapea_error(r)
    return _ok_versionada(r) or r.json()


def _err(d: dict) -> str | None:
    if "_error" not in d:
        return None
    if d["_error"] == "validacion":
        return f"No se pudo hacer: {d['_detail']}"
    detail: str = str(d["_detail"])
    return detail


def _pide_confirmacion(resumen: str, h: str) -> str:
    return (
        f"{resumen}\n\nPara confirmar responde exactamente:\n"
        f"sí {h}\n(Si los datos cambian antes, el código caduca.)"
    )


def _guardar_pendiente(chat_id: str, op: str, canon: dict, base: Any = None) -> str:
    h = ops.hash_preview(chat_id, op, canon)
    _PENDIENTES[h] = {"chat": chat_id, "op": op, "canon": canon, "base": base}
    return h
