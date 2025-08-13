# src/agents/specialists/transcription_agent.py
import logging
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from src.tools.speech_processing import transcribe_with_whisper

logger = logging.getLogger(__name__)


class SimplifiedTranscriptionState(TypedDict):
    """
    Estado simplificado y agnóstico para el grafo de transcripción.
    Solo contiene la información esencial para la tarea de transcripción.
    """

    audio_file_path: str
    transcription: str | None
    error_message: str | None


class TranscriptionAgent:
    """
    Agente especializado y agnóstico a la fuente para la transcripción de audio.
    Su única responsabilidad es transcribir un archivo de audio local.
    """

    def __init__(self):
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """
        Construye un grafo simple con un único nodo para la transcripción.
        """
        graph_builder = StateGraph(SimplifiedTranscriptionState)
        graph_builder.add_node("transcribe", self._transcribe_node)
        graph_builder.set_entry_point("transcribe")
        graph_builder.add_edge("transcribe", END)
        return graph_builder.compile()

    async def _transcribe_node(
        self, state: SimplifiedTranscriptionState
    ) -> dict[str, Any]:
        """
        Nodo que invoca la herramienta de transcripción de Whisper.
        """
        audio_path = state["audio_file_path"]
        logger.info(f"Agente de transcripción procesando: {audio_path}")
        try:
            result = await transcribe_with_whisper.ainvoke({"audio_path": audio_path})
            transcription = result.get("transcript")
            if transcription is None:
                raise ValueError("La transcripción no devolvió texto.")
            logger.info(f"Transcripción exitosa para: {audio_path}")
            return {"transcription": transcription}
        except Exception as e:
            error_message = f"Error durante la transcripción en el agente: {e}"
            logger.error(error_message, exc_info=True)
            return {"error_message": error_message}

    async def run(self, audio_file_path: str) -> SimplifiedTranscriptionState:
        """
        Ejecuta el grafo de transcripción.

        Args:
            audio_file_path: La ruta local del archivo de audio a transcribir.

        Returns:
            El estado final del grafo, que contiene la transcripción o un error.
        """
        initial_state = SimplifiedTranscriptionState(
            audio_file_path=audio_file_path,
            transcription=None,
            error_message=None,
        )
        final_state = await self.graph.ainvoke(initial_state)
        return final_state


# Instancia única del agente para ser reutilizada
transcription_agent = TranscriptionAgent()