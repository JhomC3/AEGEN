# src/agents/specialists/file_handler_specialist.py
"""
Specialist wrapper para FileHandlerAgent siguiendo el patrón de otros specialists.
Permite al MasterOrchestrator enrutar tareas de procesamiento de archivos.
"""

import logging
from typing import Any

from langchain_core.tools import BaseTool, tool
from langgraph.graph import StateGraph

from src.agents.file_handler_agent import FileHandlerAgent
from src.core.interfaces.specialist import SpecialistInterface
from src.core.registry import specialist_registry
from src.core.schemas import AgentContext, GraphStateV2

logger = logging.getLogger(__name__)


@tool
async def file_processing_tool(file_path: str, file_name: str = "") -> str:
    """
    Procesa archivos multimodales (documentos, imágenes, audio) extrayendo contenido.
    Usa FileHandlerAgent interno con validaciones y procesamiento seguro.
    """
    logger.info(f"Processing file: {file_name or file_path}")

    # Crear instancia de FileHandlerAgent
    handler = FileHandlerAgent()

    # Preparar input y context
    input_data = {
        "file_path": file_path,
        "file_name": file_name or file_path.split("/")[-1],
    }
    context = AgentContext(user_id="system", session_id="file_processing")

    try:
        result = await handler.execute(input_data, context)

        if not result.success:
            error_msg = f"File processing failed: {result.error_message}"
            logger.error(error_msg)
            return error_msg

        # Extraer contenido del resultado
        content = result.data.get("content", "")
        file_info = f"File: {result.data.get('file_name', 'unknown')}"

        return f"{file_info}\n\nContent:\n{content}"

    except Exception as e:
        error_msg = f"Error processing file {file_name}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return error_msg


class FileHandlerSpecialist(SpecialistInterface):
    """
    Specialist para procesamiento de archivos multimodales.
    Wrapper que integra FileHandlerAgent con el sistema de especialistas.
    """

    def __init__(self):
        self._name = "file_handler_specialist"
        self._graph = self._build_graph()
        self._tool: BaseTool = file_processing_tool

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
        """Este especialista maneja eventos de archivos."""
        return ["file", "document", "image", "audio"]

    def _build_graph(self) -> Any:
        """Construye grafo que procesa archivos."""
        graph_builder = StateGraph(GraphStateV2)
        graph_builder.add_node("process_file", self._process_file_node)
        graph_builder.set_entry_point("process_file")
        return graph_builder.compile()

    async def _process_file_node(self, state: GraphStateV2) -> dict[str, Any]:
        """
        Nodo que procesa archivos y actualiza el estado.
        """
        payload = state.get("payload", {})

        # Extraer información del archivo del payload
        file_path = payload.get("file_path")
        file_name = payload.get("file_name", "")

        if not file_path:
            error_msg = "No file path provided in payload"
            logger.error(error_msg)
            payload["response"] = error_msg
            payload["last_specialist"] = "file_handler_specialist"
            payload["next_action"] = "error"
            return {"payload": payload}

        logger.info(f"FileHandlerSpecialist processing: {file_name or file_path}")

        # Procesar archivo usando la herramienta
        result = await self.tool.ainvoke({
            "file_path": file_path,
            "file_name": file_name,
        })

        # Actualizar payload con resultado
        payload["response"] = result
        payload["file_content"] = result  # Para uso posterior
        payload["last_specialist"] = "file_handler_specialist"
        payload["next_action"] = "respond_to_user"

        logger.info("FileHandlerSpecialist: Processing complete")
        return {"payload": payload}


# Registrar el specialist
specialist_registry.register(FileHandlerSpecialist())
