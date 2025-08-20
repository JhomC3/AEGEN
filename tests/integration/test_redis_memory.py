#!/usr/bin/env python3
"""
Test script para verificar el funcionamiento de la memoria conversacional con Redis.
Crea una sesión de prueba y verifica la persistencia.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.core.schemas import V2ChatMessage  # noqa: E402
from src.core.session_manager import session_manager  # noqa: E402


async def test_redis_session():
    """Test básico de SessionManager con Redis."""
    test_chat_id = "test_chat_123"

    print("🧪 Testing Redis Session Manager...")

    try:
        # Test 1: Verificar que no hay sesión inicial
        initial_session = await session_manager.get_session(test_chat_id)
        print(f"✅ Sesión inicial: {initial_session is None}")

        # Test 2: Crear nueva sesión con historial
        test_history: list[V2ChatMessage] = [
            {"role": "user", "content": "Hola, ¿cómo estás?"},
            {
                "role": "assistant",
                "content": "¡Hola! Estoy bien, gracias por preguntar.",
            },
            {"role": "user", "content": "¿Puedes recordar mi nombre si te lo digo?"},
            {
                "role": "assistant",
                "content": "Sí, puedo recordar tu nombre durante nuestra conversación.",
            },
        ]

        test_state = {
            "event": None,
            "payload": {"test": "data"},
            "error_message": None,
            "conversation_history": test_history,
        }

        # Test 3: Guardar sesión
        saved = await session_manager.save_session(test_chat_id, test_state)
        print(f"✅ Sesión guardada: {saved}")

        # Test 4: Recuperar sesión
        retrieved_session = await session_manager.get_session(test_chat_id)
        print(f"✅ Sesión recuperada: {retrieved_session is not None}")

        if retrieved_session:
            history = retrieved_session["conversation_history"]
            print(f"✅ Historial recuperado: {len(history)} mensajes")
            print(f"   Último mensaje: {history[-1]['content'][:50]}...")

        # Test 5: Info de sesión
        session_info = await session_manager.get_session_info(test_chat_id)
        if session_info:
            print(
                f"✅ Info de sesión: {session_info['message_count']} mensajes, TTL: {session_info['ttl_seconds']}s"
            )

        # Test 6: Limpiar sesión de prueba
        deleted = await session_manager.delete_session(test_chat_id)
        print(f"✅ Sesión eliminada: {deleted}")

        print("🎉 ¡Todos los tests de Redis pasaron exitosamente!")

    except Exception as e:
        print(f"❌ Error en test de Redis: {e}")
        print("💡 Asegúrate de que Redis esté ejecutándose en: redis://redis:6379/1")
        print("💡 Para iniciar Redis: docker run -d -p 6379:6379 redis:alpine")
        return False

    finally:
        await session_manager.close()

    return True


if __name__ == "__main__":
    success = asyncio.run(test_redis_session())
    exit(0 if success else 1)
