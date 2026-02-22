from unittest.mock import AsyncMock

import pytest

from src.memory.milestone_extractor import (
    MilestoneData,
    MilestoneExtraction,
    MilestoneExtractor,
)


@pytest.mark.asyncio
async def test_extract_milestones(mocker):
    extractor = MilestoneExtractor()

    mock_response = MilestoneExtraction(
        milestones=[
            MilestoneData(
                action="Gimnasio",
                status="Completado",
                emotion="Cansado",
                description="Hizo ejercicio a pesar de no querer",
            )
        ]
    )

    # We replace the entire chain with a mock
    mock_chain = AsyncMock()
    mock_chain.ainvoke.return_value = mock_response
    extractor.chain = mock_chain

    text = "User: Fui al gimnasio pero estaba super cansado. \nAssistant: Qué bueno!"
    result = await extractor.extract_milestones(text)

    assert len(result) == 1
    assert result[0].action == "Gimnasio"
    assert result[0].status == "Completado"


@pytest.mark.asyncio
async def test_extract_milestones_empty(mocker):
    extractor = MilestoneExtractor()

    mock_response = MilestoneExtraction(milestones=[])
    mock_chain = AsyncMock()
    mock_chain.ainvoke.return_value = mock_response
    extractor.chain = mock_chain

    text = "User: Hola \nAssistant: Hola, cómo estás?"
    result = await extractor.extract_milestones(text)

    assert len(result) == 0


@pytest.mark.asyncio
async def test_extract_milestones_empty_input():
    extractor = MilestoneExtractor()
    result = await extractor.extract_milestones("   ")
    assert len(result) == 0
