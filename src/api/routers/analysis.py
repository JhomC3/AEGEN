# src/api/routers/analysis.py
import logging

from fastapi import APIRouter, Depends, HTTPException

# Importar la dependencia del orquestador
from src.agents.orchestrator import OrchestratorAgent
from src.core.dependencies import get_orchestrator_agent  # Asume DI
from src.core.schemas import AnalyzeQuery, AnalyzeResponse

router = APIRouter(prefix="/analyze", tags=["Analysis"])
logger = logging.getLogger(__name__)


orchestrator_dependency = Depends(get_orchestrator_agent)


@router.post("/", response_model=AnalyzeResponse)
async def analyze_request(
    request: AnalyzeQuery,
    # Inyectar el agente orquestador como dependencia
    orchestrator: OrchestratorAgent = orchestrator_dependency,
):
    """Recibe una query y la procesa a través del sistema multi-agente."""
    logger.info(f"Received analysis request via router: '{request.query}'")
    try:
        result_data = await orchestrator.process_request(request.query)
        # Aquí asumimos que process_request devuelve un dict compatible con AnalyzeResponse
        # Se podría añadir validación o transformación si es necesario
        return AnalyzeResponse(**result_data)
    except Exception as e:  # Captura general, idealmente más específica
        logger.exception(f"Unhandled error during analysis for query '{request.query}'")
        raise HTTPException(
            status_code=500, detail="An internal server error occurred."
        ) from e
    # Manejadores de excepciones específicos pueden refinar esto
