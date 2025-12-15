#!/usr/bin/env python3
"""
Script temporal para probar que la funcionalidad de memoria funciona.
"""

import asyncio
import sys
from pathlib import Path

# Agregar directorio del proyecto al path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

async def test_memory_functionality():
    """Test básico de funcionalidad de memoria."""
    try:
        from src.agents.specialists.chat_agent import _get_knowledge_context
        
        # Probar que la función de knowledge context funciona sin errores
        print("🧠 Probando integración de memory...")
        
        # Simular consulta (aunque la base esté vacía)
        context = await _get_knowledge_context("test query")
        print(f"✅ Knowledge context function works: {len(context)} chars returned")
        
        # Probar chat agent tool
        from src.agents.specialists.chat_agent import conversational_chat_tool
        
        print("💬 Probando ChatAgent con memory integration...")
        result = await conversational_chat_tool.ainvoke({
            "user_message": "Hola, ¿qué es la terapia cognitiva?",
            "conversation_history": ""
        })
        
        print(f"✅ ChatAgent response: {result[:100]}...")
        
        print("\n🎉 ÉXITO: La integración de memoria funciona correctamente!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_memory_functionality())
    exit(0 if success else 1)