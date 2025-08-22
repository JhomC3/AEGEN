# src/agents/specialists/planner/agent.py
"""
PlannerAgent implementation siguiendo Clean Architecture principles.
Single responsibility: implementar SpecialistInterface y contener business logic.
"""

import logging
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import BaseTool

from src.core.engine import llm
from src.core.interfaces.specialist import SpecialistInterface
from src.core.registry import specialist_registry
from src.core.schemas import GraphStateV2

from . import state_utils

# Import dependencies - cada una con single responsibility
from .graph_builder import PlannerGraphBuilder
from .prompt_manager import planner_prompts
from .tool import planner_tool

logger = logging.getLogger(__name__)


class PlannerAgent(SpecialistInterface):
    """
    Deep Agents Planning Tool implementation.

    Responsabilidades:
    - Implementar SpecialistInterface
    - Orquestar dependencies (prompts, graph builder, tool)
    - Contener business logic de planificación
    - Mantener coherencia conversacional

    Dependencies inyectadas:
    - PlannerGraphBuilder: Construcción de graph
    - PlannerPromptManager: Gestión de prompts
    - state_utils: Manipulación de state (pure functions)
    """

    def __init__(self):
        """Initialize PlannerAgent with dependency injection."""
        self._name = "planner_agent"
        self._tool: BaseTool = planner_tool

        # Dependency injection - cada dependency tiene single responsibility
        self._prompts = planner_prompts
        self._graph = PlannerGraphBuilder(self._planning_node).build()

    @property
    def name(self) -> str:
        """Specialist name for registry."""
        return self._name

    @property
    def graph(self) -> Any:
        """Compiled LangGraph StateGraph."""
        return self._graph

    @property
    def tool(self) -> BaseTool:
        """Tool exposed to MasterOrchestrator."""
        return self._tool

    def get_capabilities(self) -> list[str]:
        """
        Planning agent capabilities.
        Nueva arquitectura (ADR-0006): Solo maneja eventos internos de planificación.
        Los eventos "text" del usuario ahora van directamente a ChatAgent.
        """
        return ["planning", "coordination", "internal_planning_request"]

    async def _planning_node(self, state: GraphStateV2) -> dict[str, Any]:
        """
        Core business logic node - FOCUSED on planning logic only.

        Responsibilities:
        - Ejecutar lógica de planificación
        - Generar respuestas inteligentes
        - Coordinar con state utilities

        Dependencies delegated to:
        - state_utils: Para manipulación de state
        - prompt_manager: Para access a prompts
        - LLM engine: Para generation
        """
        logger.info("PlannerAgent: Ejecutando lógica de planificación...")
        logger.info(f"PlannerAgent: Estado recibido keys: {list(state.keys())}")

        try:
            # 1. Build context using pure function and transcript from chaining
            transcript = state.get("payload", {}).get("transcript", "")
            context = state_utils.build_context_from_state(state)

            # If we got transcript from TranscriptionAgent, enhance context
            if transcript:
                context += f"\n\nTRANSCRIPT FROM AUDIO: {transcript}"

            # 2. Get conversation summary using pure function
            conversation_history = state.get("conversation_history", [])
            logger.info(
                f"PlannerAgent: Historial conversacional recibido: {len(conversation_history)} mensajes"
            )
            logger.info(
                f"PlannerAgent: Historial preview: {conversation_history[-2:] if len(conversation_history) >= 2 else conversation_history}"
            )

            history_summary = state_utils.build_conversation_summary(
                conversation_history
            )
            logger.info(f"PlannerAgent: Resumen generado: {history_summary}")

            # 3. Build prompt using managed prompts
            planning_prompt = ChatPromptTemplate.from_messages([
                ("system", self._prompts.get_system_message()),
                (
                    "human",
                    f"""{self._prompts.get_decision_prompt()}

CONTEXTO ACTUAL:
{context}

HISTORIAL CONVERSACIONAL:
{history_summary}

Genera una respuesta conversacional inteligente y apropiada.""",
                ),
            ])

            # 4. Execute LLM chain - core business logic
            chain = planning_prompt | llm
            result = await chain.ainvoke({})
            response_content = str(result.content)

            # 5. Update state using pure functions
            user_content = state_utils.extract_user_content_from_state(state)
            updated_history = state_utils.update_conversation_history(
                conversation_history, user_content, response_content
            )

            # 6. Build response payload with chaining markers
            updated_payload = {
                **state.get("payload", {}),
                "response": response_content,
                "last_specialist": "planner_agent",  # Mark for chaining
                "next_action": "respond_to_user",  # Indicates final response
            }

            logger.info(
                "PlannerAgent: Planificación completada exitosamente, marcando para finalizar chain"
            )

            return {"payload": updated_payload, "conversation_history": updated_history}

        except Exception as e:
            error_msg = f"Error en planificación: {e}"
            logger.error(error_msg, exc_info=True)

            return {
                "payload": {
                    **state.get("payload", {}),
                    "error": error_msg,
                    "last_specialist": "planner_agent",
                    "next_action": "error",
                },
                "error_message": error_msg,
            }


# Register specialist following project conventions
specialist_registry.register(PlannerAgent())
