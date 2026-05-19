"""Especialista genérico basado en la configuración de un skill."""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.tools import BaseTool
from langgraph.graph import END, StateGraph

from src.agents.utils.state_utils import extract_user_content_from_state
from src.core.interfaces.specialist import SpecialistInterface
from src.core.schemas.graph import GraphStateV2
from src.personality.skill_loader import LoadedSkill

logger = logging.getLogger(__name__)


class SkillBasedSpecialist(SpecialistInterface):
    """
    Especialista que se auto-configura a partir de un SKILL.md
    y su correspondiente tools.py.
    """

    def __init__(self, loaded_skill: LoadedSkill) -> None:
        self._skill = loaded_skill
        self._manifest = loaded_skill.content.manifest
        self._tool = loaded_skill.tool
        self._name = self._manifest.id

        # Construir el grafo dinámicamente
        self._graph = self._build_graph()

    @property
    def name(self) -> str:
        return self._name

    @property
    def tool(self) -> BaseTool | None:
        return self._tool

    @property
    def graph(self) -> Any:
        return self._graph

    def get_capabilities(self) -> list[str]:
        return self._manifest.capabilities

    def _build_graph(self) -> Any:
        """Construye un LangGraph simple de un solo nodo para este especialista."""
        workflow = StateGraph(GraphStateV2)

        # El nombre del nodo es el ID del skill
        node_name = f"{self._name}_node"
        workflow.add_node(node_name, self._execute_skill)

        workflow.set_entry_point(node_name)

        # Si el skill tiene configurado un encadenamiento, el orquestador lo manejará
        # pero aquí cerramos el grafo del especialista.
        workflow.add_edge(node_name, END)

        return workflow.compile()

    async def _execute_skill(self, state: GraphStateV2) -> GraphStateV2:
        """
        Nodo de ejecución genérico. Extrae contenido e invoca el tool o worker.
        """
        payload = state.get("payload", {})
        user_message = extract_user_content_from_state(state)

        if not user_message:
            logger.warning("No user content found for skill %s", self._name)
            payload["response"] = "Lo siento, no pude procesar tu mensaje."
            return state

        # 1. Ejecutar lógica del skill (Síncrona o Asíncrona)
        response = await self._run_tool_logic(state, user_message)

        # 2. Actualizar estado y metadatos
        payload["response"] = response
        payload["last_specialist"] = self._name

        if self._name == "transcription_agent":
            payload["transcript"] = response

        # Determinar siguiente acción y actualizar historial
        self._update_next_action(payload)
        if self._manifest.requirements.update_history:
            # Creamos una lista nueva para forzar a LangGraph a detectar el cambio
            current_history = list(state.get("conversation_history", []))
            current_history.append({"role": "user", "content": user_message})
            current_history.append({"role": "assistant", "content": response})
            # Mantener solo los últimos 20 por ahora (configuración estándar)
            state["conversation_history"] = current_history[-20:]

        return state

    async def _run_tool_logic(self, state: GraphStateV2, user_message: str) -> str:
        """Decide y ejecuta la herramienta del skill."""
        tool = self._tool
        if not tool:
            return f"Modo {self._name} activo, pero sin herramientas configuradas."

        payload = state.get("payload", {})
        event = state.get("event")
        chat_id = "unknown"
        if event and hasattr(event, "chat_id"):
            chat_id = str(event.chat_id)

        tool_args = {
            "user_message": user_message,
            "chat_id": chat_id,
            "conversation_history": state.get("conversation_history", []),
            "routing_metadata": payload.get("routing_metadata", {}),
        }

        # Enriquecer argumentos desde payload
        for key in ["audio_file_path", "file_path", "image_path"]:
            if key in payload:
                tool_args[key] = payload[key]

        try:
            if self._manifest.async_capable:
                return await self._delegate_to_worker(chat_id, tool_args)
            return str(await tool.ainvoke(tool_args))
        except Exception:
            logger.exception("Error executing skill tool %s", self._name)
            return "Tuve un problema técnico al procesar tu solicitud."

    async def _delegate_to_worker(self, chat_id: str, tool_args: dict[str, Any]) -> str:
        """Spawnea un worker asíncrono para la tarea."""
        from src.agents.workers.worker_manager import WorkerManager
        from src.core.dependencies import get_event_bus

        tool = self._tool
        if not tool:
            return "Error: Herramienta no configurada para delegación."

        try:
            bus = get_event_bus()
            manager = WorkerManager(event_bus=bus)
            task_id = await manager.spawn(
                skill_id=self._name, chat_id=chat_id, tool=tool, context=tool_args
            )
            name = self._manifest.name.lower()
            return f"Entendido. Inicié una tarea de {name} (ID: {task_id})."
        except Exception:
            logger.exception("Worker spawn failed, falling back to sync")
            return str(await tool.ainvoke(tool_args))

    def _update_next_action(self, payload: dict[str, Any]) -> None:
        """Establece la siguiente acción en el flujo."""
        chain_to = self._manifest.requirements.chain_to
        payload["next_action"] = (
            f"chain_to_{chain_to}" if chain_to else "respond_to_user"
        )
