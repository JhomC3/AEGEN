import os
import sys
import asyncio
import logging
from google import genai
from google.genai import types

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Asegurar que el path de src esté disponible
sys.path.append(os.getcwd())
from src.core.config import settings

async def test_new_sdk_rag():
    api_key = settings.GOOGLE_API_KEY.get_secret_value()
    client = genai.Client(api_key=api_key)
    
    model_id = "gemini-2.5-flash-lite"
    
    # 1. Listar archivos para encontrar uno para probar
    logger.info("Listando archivos con el NUEVO SDK...")
    files = list(client.files.list())
    
    active_files = [f for f in files if f.state == 'ACTIVE']
    
    if not active_files:
        logger.error("No hay archivos activos en la File API para probar.")
        return

    test_file = active_files[0]
    logger.info(f"Probando con archivo: {test_file.display_name} (URI: {test_file.uri})")

    # 2. Intentar generar contenido
    logger.info(f"Enviando consulta a {model_id}...")
    try:
        response = client.models.generate_content(
            model=model_id,
            contents=[
                test_file,
                "Resume brevemente el contenido de este archivo en una oración."
            ]
        )
        logger.info("✅ ¡ÉXITO! La consulta RAG funcionó con el nuevo SDK.")
        logger.info(f"Respuesta: {response.text}")
    except Exception as e:
        logger.error(f"❌ FALLO con el nuevo SDK: {e}")

if __name__ == "__main__":
    asyncio.run(test_new_sdk_rag())
