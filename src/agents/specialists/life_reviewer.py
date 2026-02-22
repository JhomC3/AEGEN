import logging
from typing import cast

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from src.core.dependencies import get_sqlite_store
from src.core.engine import create_observable_config, llm_core
from src.core.messaging.outbox import outbox_manager

logger = logging.getLogger(__name__)


class ProgressAnalysis(BaseModel):
    has_progress: bool = Field(description="Si hay progreso real")
    summary: str = Field(description="Resumen del análisis")
    recommendation: str = Field(description="Recomendación/Felicitación")
    should_notify_proactively: bool = Field(description="Si debe notificar")


class LifeReviewer:
    """Análisis longitudinal del estado del usuario."""

    def __init__(self) -> None:
        self.prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "Eres el Analista de MAGI. Revisa hitos y busca progresos.\n"
                "INSTRUCCIONES:\n"
                "1. Compara registros.\n"
                "2. Busca mejoras cuantitativas/cualitativas.\n"
                "3. Genera felicitación/recomendación empática.",
            ),
            ("human", "Hitos:\n{milestones_context}"),
        ])
        # Usamos with_structured_output con el motor CORE (120B)
        self.chain = self.prompt | llm_core.with_structured_output(ProgressAnalysis)

    async def review_user_progress(self, chat_id: str) -> None:
        """Realiza la revisión y agenda notificación."""
        store = get_sqlite_store()
        milestones = await store.state_repo.get_recent_milestones(chat_id, 20)
        if not milestones:
            return

        ctx = ""
        for m in milestones:
            ctx += (
                f"- {m['created_at']} | {m['action']}: {m['status']}. "
                f"E: {m['emotion']}. D: {m['description']}\n"
            )

        config = create_observable_config("life_review")
        try:
            analysis = await self.chain.ainvoke(
                {"milestones_context": ctx},
                config=cast(RunnableConfig, config),
            )

            if (
                isinstance(analysis, ProgressAnalysis)
                and analysis.should_notify_proactively
            ):
                intent = (
                    f"Felicitar: {analysis.summary}. "
                    f"Recomendar: {analysis.recommendation}"
                )
                await outbox_manager.schedule_message(
                    chat_id=chat_id, intent=intent, delay_seconds=3600
                )
                logger.info(f"Life Review ok: {chat_id}")

        except Exception as e:
            logger.error(f"Error LifeReviewer {chat_id}: {e}")


life_reviewer = LifeReviewer()
