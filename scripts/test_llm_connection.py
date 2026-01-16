import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.core.config import settings
from src.core.engine import llm

async def verify_llm_connection():
    print(f"--- Verificando Configuración de LLM ---")
    print(f"Provider Configurado: {settings.LLM_PROVIDER}")
    print(f"Tipo de objeto LLM: {type(llm).__name__}")
    
    if settings.LLM_PROVIDER == "openrouter":
        print(f"Modelo OpenRouter: {settings.OPENROUTER_MODEL_NAME}")
        api_key = settings.OPENROUTER_API_KEY.get_secret_value() if settings.OPENROUTER_API_KEY else None
        print(f"API Key presente: {'SÍ' if api_key else 'NO'}")
    else:
        print(f"Modelo Google: {settings.DEFAULT_LLM_MODEL}")

    print("\n--- Probando Conexión (Generación simple) ---")
    try:
        response = await llm.ainvoke("Responde solo con la palabra: 'CONECTADO'")
        print(f"Respuesta del LLM: {response.content}")
        print("\n✅ VERIFICACIÓN EXITOSA")
    except Exception as e:
        print(f"\n❌ ERROR DE CONEXIÓN: {e}")
        if "api_key" in str(e).lower():
            print("Pista: Verifica que la API KEY esté correctamente configurada en el .env")

if __name__ == "__main__":
    asyncio.run(verify_llm_connection())
