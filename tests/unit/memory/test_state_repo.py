import os

import pytest

from src.memory.sqlite_store import SQLiteStore


@pytest.fixture
async def state_db():
    db_path = "storage/test_state.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    store = SQLiteStore(db_path)
    # Using the real schema to test it creates our new tables
    schema_path = "src/memory/schema.sql"
    await store.init_db(schema_path)

    yield store

    await store.disconnect()
    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.mark.asyncio
async def test_add_and_get_goals(state_db):
    chat_id = "user_123"

    # Add a goal
    goal_id = await state_db.state_repo.add_goal(
        chat_id=chat_id,
        goal_type="fitness",
        description="Ir al gimnasio 3 veces por semana",
    )

    assert goal_id > 0

    # Get active goals
    goals = await state_db.state_repo.get_active_goals(chat_id)
    assert len(goals) == 1
    assert goals[0]["description"] == "Ir al gimnasio 3 veces por semana"
    assert goals[0]["status"] == "active"

    # Update status
    success = await state_db.state_repo.update_goal_status(goal_id, "completed")
    assert success is True

    # Get active goals again
    goals_after = await state_db.state_repo.get_active_goals(chat_id)
    assert len(goals_after) == 0


@pytest.mark.asyncio
async def test_add_and_get_milestones(state_db):
    chat_id = "user_456"

    # Add a milestone
    milestone_id = await state_db.state_repo.add_milestone(
        chat_id=chat_id,
        action="Gimnasio",
        status="Completado",
        emotion="Cansado pero orgulloso",
    )

    assert milestone_id > 0

    # Get recent milestones
    milestones = await state_db.state_repo.get_recent_milestones(chat_id)
    assert len(milestones) == 1
    assert milestones[0]["action"] == "Gimnasio"
    assert milestones[0]["emotion"] == "Cansado pero orgulloso"
