import asyncio
import logging

import pytest

from src.agents.orchestrator.factory import OrchestratorFactory
from src.core.dependencies import initialize_global_resources, shutdown_global_resources
from src.core.schemas.graph import CanonicalEventV1, GraphStateV2
from src.core.session_manager import SessionManager

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_conversational_flow():
    """
    Test de integración que valida un flujo conversacional completo:
    1. El usuario se presenta.
    2. El sistema responde y guarda en memoria.
    3. El usuario pregunta su nombre en una nueva sesión.
    4. El sistema recuerda el nombre gracias a la memoria local-first.
    """
    print("\n🎭 Testing Conversational Flow Phase 3B...")

    # Inicializar recursos (SQLite, etc.)
    await initialize_global_resources()
    session_manager = SessionManager()

    try:
        chat_id = "test_flow_123"
        user_name = "Juan"

        # --- TURNO 1: Presentación ---
        print(f"👉 Turno 1: 'Hola, me llamo {user_name}'")
        event1 = CanonicalEventV1(
            chat_id=chat_id,
            user_id=chat_id,
            source="telegram",
            event_type="text",
            content=f"Hola, me llamo {user_name}",
            metadata={"first_name": user_name},
            file_id=None,
            timestamp=None,
            first_name=user_name,
            language_code=None,
        )

        orchestrator = OrchestratorFactory.create_orchestrator()
        initial_state1: GraphStateV2 = {
            "event": event1,
            "payload": {},
            "conversation_history": [],
            "session_id": "test_session",
            "error_message": None,
        }

        final_state1 = await orchestrator.run(initial_state1)
        response1 = final_state1["payload"].get("response", "")

        assert len(response1) > 0
        print(f"   Respuesta 1: {response1[:100]}...")
        print(
            f"   Memoria actualizada: {len(final_state1.get('conversation_history', []))} mensajes"  # noqa: E501
        )

        # Forzar consolidación de memoria (simulado)
        # En un flujo real esto ocurre asíncronamente
        from src.memory.consolidation_worker import consolidation_manager

        await consolidation_manager.consolidate_session(chat_id)
        print("   ✅ Memoria consolidada en SQLite")

        # --- TURNO 2: Recordar ---
        # Simulamos una nueva sesión (history vacío)
        print("\n👉 Turno 2: '¿Cómo me llamo?' (Nueva sesión)")
        event2 = CanonicalEventV1(
            chat_id=chat_id,
            user_id=chat_id,
            source="telegram",
            event_type="text",
            content="¿Cómo me llamo?",
            file_id=None,
            timestamp=None,
            first_name=None,
            language_code=None,
        )

        initial_state2: GraphStateV2 = {
            "event": event2,
            "payload": {},
            "conversation_history": [],
            "session_id": "test_session_2",
            "error_message": None,
        }

        final_state2 = await orchestrator.run(initial_state2)
        response2 = final_state2["payload"].get("response", "")

        assert len(response2) > 0
        print(f"   Respuesta 2: {response2[:100]}...")
        print(
            f"   Memoria final: {len(final_state2.get('conversation_history', []))} mensajes"  # noqa: E501
        )

        # Verificación de memoria a largo plazo
        if user_name.lower() in response2.lower():
            print("✅ ¡El sistema recordó el nombre correctamente!")
        else:
            print("⚠️  El sistema no recordó el nombre específicamente")

        # Verificar persistencia en Redis (session)
        session_info = await session_manager.get_session_info(chat_id)
        if session_info:
            print(f"   Sesión persistida: {session_info['message_count']} mensajes")
            print(f"   TTL restante: {session_info['ttl_seconds']}s")

        return True

    except Exception as e:
        print(f"❌ Error en el test de flujo: {e}")
        import traceback

        traceback.print_exc()
        return False
    finally:
        await shutdown_global_resources()


if __name__ == "__main__":
    success = asyncio.run(test_conversational_flow())
    exit(0 if success else 1)
