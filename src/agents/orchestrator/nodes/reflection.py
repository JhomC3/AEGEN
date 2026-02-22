import logging
from typing import cast

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from src.core.engine import create_observable_config, llm_core
from src.core.messaging.outbox import outbox_manager
from src.core.schemas import GraphStateV2

logger = logging.getLogger(__name__)


class ReflectionDecision(BaseModel):
    should_follow_up: bool = Field(description="Si inicia seguimiento")
    reasoning: str = Field(description="Explicación")
    follow_up_intent: str | None = Field(None, description="Intención")
    delay_hours: int = Field(default=4, description="Horas espera")


class LifeReflectionNode:
    """Nodo de reflexión para agendar seguimientos proactivos."""

    def __init__(self) -> None:
        self.prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "Eres el Analista de MAGI. Detecta planes o hitos importantes.\n"
                "REGLAS:\n"
                "1. Agenda seguimiento si hay planes (ej: gimnasio, médico).\n"
                "2. Agenda seguimiento tras malestar acordado.\n"
                "3. NO para trivialidades.\n"
                "4. Intent corto.\n"
                "5. delay: 4-24h.\n\n"
                "DEBES responder llamando a la función ReflectionDecision.",
            ),
            ("human", "H: {history}\n\nR: {response}"),
        ])
        self.chain = self.prompt | llm_core.with_structured_output(ReflectionDecision)

    async def run(self, state: GraphStateV2) -> GraphStateV2:
        """Procesa el estado para agendar seguimientos."""
        session_id = state.get("session_id", "unknown")
        payload = state.get("payload", {})
        response = payload.get("response")

        if not response:
            return state

        history_msgs = state.get("conversation_history", [])[-4:]
        history_text = "\n".join([
            f"{m.get('role', 'u')}: {m.get('content', '')}" for m in history_msgs
        ])
        history_text += f"\nuser: {state['event'].content}"

        config = create_observable_config("life_reflection")
        try:
            decision = await self.chain.ainvoke(
                {"history": history_text, "response": str(response)},
                config=cast(RunnableConfig, config),
            )

            if (
                isinstance(decision, ReflectionDecision)
                and decision.should_follow_up
                and decision.follow_up_intent
            ):
                chat_id = str(state["event"].chat_id)
                delay_secs = decision.delay_hours * 3600

                msg_id = await outbox_manager.schedule_message(
                    chat_id=chat_id,
                    intent=decision.follow_up_intent,
                    delay_seconds=delay_secs,
                )

                logger.info(f"[{session_id}] Agendado ({msg_id})")

                if "metadata" not in state["payload"]:
                    state["payload"]["metadata"] = {}
                state["payload"]["metadata"]["proactive_scheduled"] = True
                state["payload"]["metadata"]["proactive_intent"] = (
                    decision.follow_up_intent
                )

        except Exception as e:
            # Fallback: No agendar nada si el LLM falla o no usa la herramienta
            logger.warning(f"[{session_id}] Skip reflection follow-up: {e}")

        return state


life_reflection_node = LifeReflectionNode()
