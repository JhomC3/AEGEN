# src/agents/specialists/transcription_agent.py
import logging
from typing import Any

from langchain_core.tools import BaseTool, tool
from langgraph.graph import StateGraph

from src.core.interfaces.specialist import SpecialistInterface
from src.core.registry import specialist_registry
from src.core.schemas import GraphStateV2
from src.tools.speech_processing import transcribe_audio

logger = logging.getLogger(__name__)


@tool
async def transcription_tool(audio_file_path: str) -> str:
    """
    Usa esta herramienta para transcribir un archivo de audio a texto.
    Recibe la ruta local del archivo de audio y devuelve la transcripción.
    """
    logger.info(f"Herramienta de transcripción procesando: {audio_file_path}")
    try:
        result = await transcribe_audio.ainvoke({"audio_path": audio_file_path})
        transcription = result.get("transcript")
        if not isinstance(transcription, str):
            raise ValueError("La transcripción no devolvió un string válido.")
        logger.info(f"Transcripción exitosa para: {audio_file_path}")
        return transcription
    except Exception as e:
        error_message = f"Error durante la transcripción en la herramienta: {e}"
        logger.error(error_message, exc_info=True)
        return error_message


class TranscriptionSpecialist(SpecialistInterface):
    """
    Agente especializado en la transcripción de audio.
    """

    def __init__(self):
        self._name: str = "transcription_agent"
        self._graph: Any = self._build_graph()
        self._tool: BaseTool = transcription_tool

    @property
    def name(self) -> str:
        return self._name

    @property
    def graph(self) -> Any:
        return self._graph

    @property
    def tool(self) -> BaseTool:
        return self._tool

    def get_capabilities(self) -> list[str]:
        """Este especialista maneja eventos de tipo audio."""
        return ["audio"]

    def _build_graph(self) -> Any:
        """
        Construye el grafo que invoca la herramienta de transcripción.
        Chaining: Ahora retorna estado para que MasterOrchestrator continúe la cadena.
        """
        graph_builder = StateGraph(GraphStateV2)
        graph_builder.add_node("transcribe", self._transcribe_node)
        graph_builder.set_entry_point("transcribe")
        # REMOVED: graph_builder.add_edge("transcribe", END)
        # Now: MasterOrchestrator handles chaining
        return graph_builder.compile()

    async def _transcribe_node(self, state: GraphStateV2) -> dict[str, Any]:
        """
        Nodo que invoca la herramienta de transcripción y actualiza el estado.
        Marks last_specialist for chaining in MasterOrchestrator.
        """
        payload = state.get("payload", {})
        audio_path = payload.get("audio_file_path")

        if not audio_path or not isinstance(audio_path, str):
            error_msg = "Error: No se proporcionó una ruta de archivo de audio válida."
            logger.error(error_msg)
            payload["response"] = error_msg
            payload["last_specialist"] = self.name
            payload["next_action"] = "error"
            return {"payload": payload}

        logger.info(f"TranscriptionAgent: Procesando audio {audio_path}")
        result = await self.tool.ainvoke({"audio_file_path": audio_path})

        # Marcar para chaining: transcription → planner (Phase 3B UX fix)
        payload["transcript"] = result  # Para que PlannerAgent use el texto
        payload["response"] = result  # Mantener compatibilidad
        payload["last_specialist"] = "transcription_agent"
        payload["next_action"] = "chain_to_planner"  # Indica que debe encadenar

        logger.info(
            "TranscriptionAgent: Transcripción completada, marcando para chain a PlannerAgent"
        )
        return {"payload": payload}


# Registrar la instancia del especialista
specialist_registry.register(TranscriptionSpecialist())
