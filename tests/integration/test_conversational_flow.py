#!/usr/bin/env python3
"""
Test del flujo conversacional completo Phase 3B:
Audio → Transcript → ChatBot → Respuesta inteligente + Memoria
"""

import asyncio
import sys
from pathlib import Path
from uuid import uuid4

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.agents.orchestrator import master_orchestrator  # noqa: E402
from src.core import schemas  # noqa: E402
from src.core.dependencies import (  # noqa: E402
    initialize_global_resources,
    shutdown_global_resources,
)
from src.core.session_manager import session_manager  # noqa: E402


async def test_conversational_flow():
    """Test completo del flujo conversacional con memoria."""
    chat_id = "test_conv_flow_456"

    print("🎭 Testing Conversational Flow Phase 3B...")

    # Inicializar recursos (SQLite, etc.)
    await initialize_global_resources()

    try:
        # Test 1: Primer mensaje de texto (nueva conversación)
        print("\n📝 Test 1: Primer mensaje de texto")

        event1 = schemas.CanonicalEventV1(
            event_id=uuid4(),
            event_type="text",
            source="telegram",
            chat_id=chat_id,
            user_id=chat_id,
            content="Hola, mi nombre es Juan y me gusta la tecnología",
            timestamp="2023-01-01T00:00:00",
            file_id=None,
            first_name="Juan",
            language_code="es",
        )

        # Simular carga de sesión existente (debería ser None)
        existing_session = await session_manager.get_session(str(chat_id))
        initial_state: schemas.GraphStateV2 = {
            "event": event1,
            "payload": {},
            "error_message": None,
            "session_id": str(chat_id),
            "conversation_history": existing_session["conversation_history"]
            if existing_session
            else [],
        }

        print(
            f"   Memoria inicial: {len(initial_state['conversation_history'])} mensajes"
        )

        # Ejecutar orquestación
        final_state1 = await master_orchestrator.run(initial_state)

        # Guardar sesión
        await session_manager.save_session(str(chat_id), final_state1)

        response1 = final_state1.get("payload", {}).get("response", "No response")
        print(f"   Respuesta 1: {response1[:100]}...")
        print(
            f"   Memoria actualizada: {len(final_state1.get('conversation_history', []))} mensajes"
        )

        # Test 2: Segundo mensaje que requiere memoria
        print("\n🧠 Test 2: Segundo mensaje (debe recordar contexto)")

        event2 = schemas.CanonicalEventV1(
            event_id=uuid4(),
            event_type="text",
            source="telegram",
            chat_id=chat_id,
            user_id=chat_id,
            content="¿Recuerdas mi nombre?",
            timestamp="2023-01-01T00:01:00",
            file_id=None,
            first_name="Juan",
            language_code="es",
        )

        # Cargar sesión existente
        existing_session2 = await session_manager.get_session(str(chat_id))
        initial_state2: schemas.GraphStateV2 = {
            "event": event2,
            "payload": {},
            "error_message": None,
            "session_id": str(chat_id),
            "conversation_history": existing_session2["conversation_history"]
            if existing_session2
            else [],
        }

        print(
            f"   Memoria cargada: {len(initial_state2['conversation_history'])} mensajes"
        )

        # Ejecutar orquestación
        final_state2 = await master_orchestrator.run(initial_state2)

        # Guardar sesión actualizada
        await session_manager.save_session(str(chat_id), final_state2)

        response2 = final_state2.get("payload", {}).get("response", "No response")
        print(f"   Respuesta 2: {response2[:100]}...")
        print(
            f"   Memoria final: {len(final_state2.get('conversation_history', []))} mensajes"
        )

        # Verificar que la respuesta menciona el nombre
        if "juan" in response2.lower():
            print("✅ ¡El sistema recordó el nombre correctamente!")
        else:
            print("⚠️  El sistema no recordó el nombre específicamente")

        # Test 3: Verificar persistencia
        print("\n💾 Test 3: Verificar persistencia de memoria")
        session_info = await session_manager.get_session_info(str(chat_id))
        if session_info:
            print(f"   Sesión persistida: {session_info['message_count']} mensajes")
            print(f"   TTL restante: {session_info['ttl_seconds']}s")

        print("\n🎉 ¡Test conversacional completado exitosamente!")

        return True

    except Exception as e:
        print(f"❌ Error en test conversacional: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        # Limpiar sesión de prueba
        await session_manager.delete_session(str(chat_id))
        await session_manager.close()
        await shutdown_global_resources()


if __name__ == "__main__":
    success = asyncio.run(test_conversational_flow())
    exit(0 if success else 1)
