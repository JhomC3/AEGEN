import logging
from typing import cast

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from src.core.engine import create_observable_config, llm_core

logger = logging.getLogger(__name__)


class MilestoneData(BaseModel):
    action: str = Field(description="Acción que ocurrió. Ej: Entrenamiento, Examen")
    status: str = Field(description="Estado: Completado, Fallido, Ocurrido")
    emotion: str | None = Field(
        None,
        description="Emoción. Ej: Apatía, Orgullo",
    )
    description: str | None = Field(None, description="Contexto breve adicional")


class MilestoneExtraction(BaseModel):
    milestones: list[MilestoneData] = Field(
        default_factory=list,
        description="Lista de hitos vitales detectados en la conversación",
    )


class MilestoneExtractor:
    """Analiza una conversación para extraer hitos vitales del usuario."""

    def __init__(self) -> None:
        self.prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "Analiza la conversación y extrae hitos importantes.\n"
                "Un hito es una acción concreta (ej. ir al gimnasio, tener una crisis) "
                "que tiene impacto en su estado físico, mental o financiero.\n"
                "NO extraigas opiniones genéricas o conversaciones triviales.\n"
                "Si no hay hitos claros, devuelve una lista vacía.",
            ),
            ("human", "{conversation}"),
        ])
        # Usamos with_structured_output con el motor CORE (120B)
        self.chain = self.prompt | llm_core.with_structured_output(
            MilestoneExtraction
        )

    async def extract_milestones(self, conversation_text: str) -> list[MilestoneData]:
        if not conversation_text.strip():
            return []

        config = create_observable_config("milestone_extraction")
        try:
            result = await self.chain.ainvoke(
                {"conversation": conversation_text},
                config=cast(RunnableConfig, config),
            )
            # The structured output should return a MilestoneExtraction instance
            if isinstance(result, MilestoneExtraction):
                return result.milestones
            return []
        except Exception as e:
            logger.error("Error extracting milestones: %s", e)
            return []


milestone_extractor = MilestoneExtractor()
