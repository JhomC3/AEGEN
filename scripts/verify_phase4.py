# scripts/verify_phase4.py
import asyncio
import logging
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from src.core.config import settings
from src.core.dependencies import initialize_global_resources, shutdown_global_resources
from src.memory.consolidation_worker import consolidation_manager

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_consolidation():
    print(f"\nTesting session consolidation at: {settings.SQLITE_DB_PATH}")

    # 1. Initialize global resources (SQLite)
    # Mock Redis to avoid connection errors
    with patch("redis.asyncio.from_url") as mock_redis_url:
        mock_redis = AsyncMock()
        mock_redis_url.return_value = mock_redis

        await initialize_global_resources()
        print("✅ Global resources initialized (Redis mocked)")

        try:
            chat_id = "test_verify_phase4"

            # 2. Mock Buffer Data
            fake_data = {
                "summary": "Resumen previo inexistente.",
                "buffer": [
                    {
                        "role": "user",
                        "content": "Hola MAGI, mi nombre es Juan y me gusta programar en Python.",
                    },
                    {
                        "role": "assistant",
                        "content": "Hola Juan, un gusto. Python es excelente.",
                    },
                    {
                        "role": "user",
                        "content": "Actualmente estoy trabajando en un proyecto de IA con SQLite.",
                    },
                    {
                        "role": "assistant",
                        "content": "Interesante. SQLite es muy versátil para almacenamiento local.",
                    },
                    {
                        "role": "user",
                        "content": "Mi meta es terminar este prototipo para el viernes.",
                    },
                ],
            }

            with patch(
                "src.memory.long_term_memory.long_term_memory.get_summary",
                return_value=fake_data,
            ):
                with patch(
                    "src.memory.long_term_memory.long_term_memory.update_memory",
                    new_callable=AsyncMock,
                ):
                    with patch(
                        "src.memory.long_term_memory.long_term_memory.get_buffer"
                    ) as mock_get_buffer:
                        # Setup mock buffer for clear_buffer
                        mock_buffer = AsyncMock()
                        mock_get_buffer.return_value = mock_buffer

                        # 3. Trigger Consolidation
                        print("\n🚀 Triggering consolidation...")
                        await consolidation_manager.consolidate_session(chat_id)

                        # 4. Verify results in SQLite
                        from src.core.dependencies import get_sqlite_store

                        store = get_sqlite_store()
                        db = await store.get_db()

                        print("\n🔍 Verifying results in SQLite:")

                        # Check summary/facts/logs
                        async with db.execute(
                            "SELECT content, memory_type FROM memories WHERE chat_id = ?",
                            (chat_id,),
                        ) as cursor:
                            rows = list(await cursor.fetchall())
                            print(
                                f"📊 Found {len(rows)} memories in SQLite for this chat"
                            )
                            for row in rows:
                                print(
                                    f"   • [{row['memory_type']}] {row['content'][:100]}..."
                                )

                            assert any(
                                row["memory_type"] == "fact" for row in rows
                            ), "❌ Facts not found!"
                            assert any(
                                row["memory_type"] == "document" for row in rows
                            ), "❌ Session log not found!"

            print("\n" + "=" * 50)
            print("✅ PHASE 4 VERIFICATION SUCCESSFUL (with partial mocks)!")
            print("=" * 50 + "\n")

        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback

            traceback.print_exc()
        finally:
            await shutdown_global_resources()


if __name__ == "__main__":
    asyncio.run(test_consolidation())
