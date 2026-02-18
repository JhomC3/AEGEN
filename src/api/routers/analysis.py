# src/api/routers/analysis.py
import logging
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status

from src.core.dependencies import get_event_bus
from src.core.interfaces.bus import IEventBus
from src.core.middleware import correlation_id
from src.core.schemas import AnalyzeQuery, IngestionResponse

router = APIRouter(tags=["Analysis"])
logger = logging.getLogger(__name__)

event_bus_dependency = Depends(get_event_bus)


@router.post(
    "/ingest",
    response_model=IngestionResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Ingests a query for asynchronous processing",
    description="Receives a query, publishes it to the event bus for processing, and returns immediately.",
)
async def ingest_request(
    request: AnalyzeQuery,
    event_bus: IEventBus = event_bus_dependency,
) -> IngestionResponse:
    """
    Endpoint de ingestión no bloqueante.

    Acepta una consulta, la envuelve en un evento con un ID de tarea único y
    la publica en el bus de eventos.
    """
    task_id = str(uuid4())
    trace_id = correlation_id.get()
    logger.info(f"Received ingestion request. Assigning TaskID: {task_id}")

    # El nombre de la tarea podría ser dinámico en el futuro
    task_name = "research_task"

    event = {
        "task_id": task_id,
        "trace_id": trace_id,
        "task_name": task_name,
        "query": request.query,
        "user_id": request.user_id,
        "session_id": str(request.session_id) if request.session_id else None,
    }

    try:
        await event_bus.publish("workflow_tasks", event)
        logger.info(f"Task {task_id} published to 'workflow_tasks' topic.")
        return IngestionResponse(
            task_id=task_id, message="Request accepted for processing."
        )
    except Exception as e:
        logger.exception(f"Failed to publish task {task_id} to the event bus.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to queue request due to an internal event bus error.",
        ) from e
