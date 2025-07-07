# src/agents/orchestrator.py
import asyncio
import logging
from datetime import UTC, datetime
from uuid import uuid4

# Importar excepciones si este agente las puede lanzar
from src.core.exceptions import AgentError, LLMConnectionError

# Importar schemas para la respuesta
from src.core.schemas import AnalysisDetails, AnalysisFinding, AnalysisStatus

# Importar dependencias (stubs de otros agentes)
# from .planner import PlannerAgent
# from .analyst import AnalystAgent
# from .presenter import PresenterAgent
# from ..tools.knowledge_source_tool import youtube_tool

logger = logging.getLogger(__name__)


class OrchestratorAgent:
    def __init__(
        self, planner=None, analyst=None, presenter=None
    ):  # Acepta otros agentes como dependencias
        # self.planner: PlannerAgent = planner
        # self.analyst: AnalystAgent = analyst
        # self.presenter: PresenterAgent = presenter
        # self.youtube_tool = youtube_tool # Ejemplo de tool inyectada
        logger.info("OrchestratorAgent instance created (stub).")
        # Este init no debe hacer I/O pesado ni cargar modelos. Eso va en initialize_global_resources.

    async def process_request(self, user_query: str) -> dict:
        """
        Procesa la solicitud del usuario orquestando otros agentes.
        Devuelve un diccionario compatible con el esquema AnalyzeResponse.
        """
        request_id = uuid4()
        logger.info(
            f"[ReqID: {request_id}] Orchestrator processing query: '{user_query}'"
        )

        try:
            # --- 1. Planificación (Stub) ---
            logger.debug(f"[ReqID: {request_id}] Delegating to Planner (stub)...")
            # plan = await self.planner.create_plan(user_query, request_id)
            await asyncio.sleep(0.05)  # Simular trabajo
            plan_stub = {
                "plan_id": uuid4(),
                "original_query": user_query,
                "steps": [
                    {
                        "step_id": 1,
                        "action": "Fetch YouTube transcripts for keywords",
                        "tool_to_use": "youtube_search_tool",
                        "expected_output_description": "List of transcripts",
                    },
                    {
                        "step_id": 2,
                        "action": "Analyze sentiment of transcripts",
                        "tool_to_use": "sentiment_analyzer_llm",
                        "expected_output_description": "Sentiment score and summary",
                    },
                ],
                # "report_format_requested": ReportFormat.TEXT_SUMMARY
            }
            logger.debug(
                f"[ReqID: {request_id}] Received plan (stub): {plan_stub['plan_id']}"
            )

            # --- 2. Adquisición de Datos (Stub) ---
            logger.debug(f"[ReqID: {request_id}] Simulating Data Acquisition (stub)...")
            # data_from_tools = {}
            # for step in plan_stub['steps']:
            #     if step['tool_to_use'] == "youtube_search_tool":
            #         # data_from_tools['transcripts'] = await self.youtube_tool.arun(...)
            #         await asyncio.sleep(0.1) # Simular llamada a tool
            #         data_from_tools['transcripts'] = ["Stub transcript 1", "Stub transcript 2"]
            data_stub = {
                "youtube_transcripts": ["Stub transcript 1", "Stub transcript 2"],
                "sentiment_scores_raw": [0.8, -0.2],
            }
            logger.debug(
                f"[ReqID: {request_id}] Acquired data (stub): {list(data_stub.keys())}"
            )

            # --- 3. Análisis (Stub) ---
            logger.debug(f"[ReqID: {request_id}] Delegating to Analyst (stub)...")
            # analysis_details_obj = await self.analyst.analyze(data_stub, plan_stub, request_id)
            await asyncio.sleep(0.05)  # Simular trabajo
            analysis_details_stub = AnalysisDetails(
                summary=f"Analysis stub for '{user_query}': Key insights identified from stub data.",
                key_findings=[
                    AnalysisFinding(
                        id=uuid4(),
                        description="Stub Finding: Positive sentiment in transcript 1.",
                        severity="medium",
                        confidence=0.75,
                        source_ids=["youtube_transcript_1"],
                        metadata={},
                    ),
                    AnalysisFinding(
                        id=uuid4(),
                        description="Stub Finding: Negative sentiment in transcript 2.",
                        severity="low",
                        confidence=0.60,
                        source_ids=["youtube_transcript_2"],
                        metadata={},
                    ),
                ],
                data_sources_used=["Stubbed YouTube Transcripts"],
            )
            logger.debug(f"[ReqID: {request_id}] Received analysis details (stub).")

            # --- 4. Presentación (Stub) ---
            logger.debug(f"[ReqID: {request_id}] Delegating to Presenter (stub)...")
            # report_content = await self.presenter.generate_report(analysis_details_obj, plan_stub['report_format_requested'], request_id)
            await asyncio.sleep(0.02)  # Simular trabajo
            report_content_stub = f"**Final Report Stub (Query: '{user_query}')**\n\n{analysis_details_stub.summary}\n\nKey Findings:\n"
            for finding in analysis_details_stub.key_findings:
                report_content_stub += (
                    f"- {finding.description} (Severity: {finding.severity or 'N/A'})\n"
                )
            logger.info(f"[ReqID: {request_id}] Final report content generated (stub).")

            # --- 5. Construir Respuesta Final ---
            final_response = {
                "request_id": request_id,
                "status": AnalysisStatus.COMPLETED_STUB,
                "query_received": user_query,
                "report_generated_at": datetime.now(UTC).isoformat(),
                # "report_format": plan_stub['report_format_requested'],
                "report_content": report_content_stub,
                "details": analysis_details_stub.model_dump(),  # Convertir Pydantic a dict
            }
            return final_response

        except LLMConnectionError as e:  # Ejemplo de manejo de excepción específica
            logger.error(
                f"[ReqID: {request_id}] LLM Connection Error during processing: {e.message}"
            )
            raise  # Re-lanzar para que el manejador de FastAPI la capture
        except AgentError as e:
            logger.error(
                f"[ReqID: {request_id}] Agent Error from {e.agent_name}: {e.message}"
            )
            raise
        except Exception as e:
            logger.exception(
                f"[ReqID: {request_id}] Unexpected error in Orchestrator process_request"
            )
            # Envolver en una excepción de aplicación si se quiere estandarizar el error
            raise AgentError(
                message=f"Orchestrator failed: {str(e)}", agent_name="Orchestrator"
            ) from e
