# src/agents/specialists/transcription_agent.py
import logging
from typing import Any

from langgraph.graph import END, StateGraph

from src.core.schemas import GraphStateV1
from src.tools.speech_processing import transcribe_with_whisper

logger = logging.getLogger(__name__)


class TranscriptionAgent:
    """
    Agente especializado y agnóstico a la fuente para la transcripción de audio.
    Su única responsabilidad es transcribir un archivo de audio local.
    Utiliza el estado de grafo estandarizado (GraphStateV1).
    """

    def __init__(self):
        self.graph: Any = self._build_graph()

    def _build_graph(self) -> Any:  # noqa: ANN401
        """
        Construye un grafo simple con un único nodo para la transcripción.
        """
        graph_builder = StateGraph(GraphStateV1)
        graph_builder.add_node("transcribe", self._transcribe_node)
        graph_builder.set_entry_point("transcribe")
        graph_builder.add_edge("transcribe", END)
        return graph_builder.compile()

    async def _transcribe_node(self, state: GraphStateV1) -> dict[str, Any]:
        """
        Nodo que invoca la herramienta de transcripción de Whisper.
        Espera la ruta del audio en `state.payload`.
        """
        audio_path = state.payload.get("audio_file_path")
        if not audio_path:
            error_message = "No se encontró 'audio_file_path' en el payload del estado."
            logger.error(error_message)
            return {"error_message": error_message}

        logger.info(f"Agente de transcripción procesando: {audio_path}")
        try:
            result = await transcribe_with_whisper.ainvoke({"audio_path": audio_path})
            transcription = result.get("transcript")
            if transcription is None:
                raise ValueError("La transcripción no devolvió texto.")
            logger.info(f"Transcripción exitosa para: {audio_path}")
            # Retorna solo los campos que deben actualizarse en el estado
            return {"payload": {**state.payload, "transcription": transcription}}
        except Exception as e:
            error_message = f"Error durante la transcripción en el agente: {e}"
            logger.error(error_message, exc_info=True)
            return {"error_message": error_message}

    async def run(self, initial_state: GraphStateV1) -> GraphStateV1:
        """
        Ejecuta el grafo de transcripción.

        Args:
            initial_state: El estado inicial del grafo, que debe contener
                           el evento y el payload con 'audio_file_path'.

        Returns:
            El estado final del grafo como un objeto GraphStateV1 validado.
        """
        final_state_dict = await self.graph.ainvoke(initial_state)
        return GraphStateV1.model_validate(final_state_dict)


# Instancia única del agente para ser reutilizada
transcription_agent = TranscriptionAgent()
