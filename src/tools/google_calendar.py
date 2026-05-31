# src/tools/google_calendar.py
"""
Google Calendar Tool — Integracion con Google Calendar.

Permite a MAGI consultar, crear y gestionar eventos del calendario.
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


async def _get_calendar_service() -> Any | None:
    """Obtiene el servicio de Google Calendar."""
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        from src.core.config import settings

        credentials_json = settings.GOOGLE_CREDENTIALS_JSON
        if not credentials_json:
            logger.warning("[CALENDAR] GOOGLE_CREDENTIALS_JSON no configurado")
            return None

        import json

        creds = Credentials.from_authorized_user_info(
            json.loads(credentials_json),
            scopes=["https://www.googleapis.com/auth/calendar.readonly"],
        )
        return build("calendar", "v3", credentials=creds)

    except ImportError:
        logger.warning(
            "[CALENDAR] google-api-python-client no instalado. "
            "pip install google-api-python-client"
        )
        return None
    except Exception as e:
        logger.warning("[CALENDAR] Error inicializando servicio: %s", e)
        return None


@tool
async def get_calendar_events(
    days_ahead: int = 7,
    max_events: int = 10,
) -> str:
    """
    Obtiene los eventos proximos del calendario de Google.

    Args:
        days_ahead: Numero de dias hacia adelante a consultar.
        max_events: Maximo de eventos a retornar.

    Returns:
        Lista de eventos formateados como texto.
    """
    service = await _get_calendar_service()
    if not service:
        return (
            "El calendario de Google no esta configurado. "
            "Configura GOOGLE_CREDENTIALS_JSON en el .env."
        )

    try:
        now = datetime.now(UTC)
        end = now + timedelta(days=days_ahead)

        events_result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=now.isoformat(),
                timeMax=end.isoformat(),
                maxResults=max_events,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )

        events = events_result.get("items", [])

        if not events:
            return "No hay eventos proximos en tu calendario."

        lines = [f"Tienes {len(events)} evento(s) en los proximos {days_ahead} dias:\n"]
        for event in events:
            start = event.get("start", {})
            date_str = start.get("dateTime", start.get("date", ""))
            summary = event.get("summary", "Sin titulo")
            location = event.get("location", "")

            line = f"- **{summary}**"
            if date_str:
                line += f" ({date_str[:16]})"
            if location:
                line += f" en {location}"
            lines.append(line)

        return "\n".join(lines)

    except Exception as e:
        logger.warning("[CALENDAR] Error consultando eventos: %s", e)
        return "No pude consultar tu calendario en este momento."


@tool
async def create_calendar_event(
    summary: str,
    start_time: str,
    duration_minutes: int = 60,
    description: str = "",
    location: str = "",
) -> str:
    """
    Crea un nuevo evento en Google Calendar.

    Args:
        summary: Titulo del evento.
        start_time: Hora de inicio en formato ISO 8601.
        duration_minutes: Duracion en minutos (default: 60).
        description: Descripcion del evento.
        location: Ubicacion del evento.

    Returns:
        Confirmacion de creacion del evento.
    """
    service = await _get_calendar_service()
    if not service:
        return (
            "El calendario de Google no esta configurado. "
            "Configura GOOGLE_CREDENTIALS_JSON en el .env."
        )

    try:
        start_dt = datetime.fromisoformat(start_time)
        if start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=UTC)

        end_dt = start_dt + timedelta(minutes=duration_minutes)

        event_body = {
            "summary": summary,
            "description": description,
            "location": location,
            "start": {"dateTime": start_dt.isoformat(), "timeZone": "UTC"},
            "end": {"dateTime": end_dt.isoformat(), "timeZone": "UTC"},
        }

        event = service.events().insert(calendarId="primary", body=event_body).execute()

        logger.info("[CALENDAR] Evento creado: %s (%s)", summary, event.get("id"))
        return f"Evento '{summary}' creado exitosamente. ID: {event.get('id')}"

    except Exception as e:
        logger.warning("[CALENDAR] Error creando evento: %s", e)
        return f"No pude crear el evento: {e}"
