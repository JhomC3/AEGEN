
import asyncio
import os
import sys

# Add project root to path
sys.path.append("/app")

# Set dummy env vars if not present (although they should be in the container)
# os.environ.setdefault("GOOGLE_API_KEY", "...") 

from src.tools.google_file_search import file_search_tool
from src.core.config import settings

async def main():
    print("--- INICIANDO VERIFICACIÓN GOOGLE RAG ---")
    
    # 1. Verificar versión
    try:
        from google import genai
        print(f"SDK Version: {getattr(genai, '__version__', 'unknown')}")
    except ImportError:
        print("CRITICO: google.genai no instalado")
        return

    # 2. Crear archivo dummy
    dummy_file = "/tmp/test_verification.txt"
    with open(dummy_file, "w") as f:
        f.write("El estoicismo enseña que debemos diferenciar lo que controlamos de lo que no. "
                "Controlamos nuestras opiniones, impulsos y deseos.")
    
    print(f"Archivo local creado: {dummy_file}")

    try:
        # 3. Probar Upload
        print("Probando upload_file...")
        uploaded = await file_search_tool.upload_file(dummy_file, display_name="VERIFICATION_TEST_FILE")
        print(f"Upload exitoso: {uploaded.name} ({uploaded.uri})")

        # Esperar brevemente a que se procese (aunque suele ser rápido para texto)
        await asyncio.sleep(2)

        # 4. Probar Query (Smart RAG)
        print("Probando query_files...")
        # Simular chat_id y buscar este archivo específico
        # (El tool filtra por nombre o tag, vamos a asegurarnos que lo encuentre)
        # Hack: forzamos el cache para que incluya este archivo recién subido
        # o confiamos en que list_files lo traiga.
        
        # Para que get_relevant_files lo encuentre, debe tener TAG o ser User_Vault.
        # El upload usó display_name="VERIFICATION_TEST_FILE".
        # get_relevant_files busca tags en el nombre.
        # Vamos a pasar un tag que coincida.
        
        query = "¿Qué enseña el estoicismo sobre el control?"
        # Pasamos "VERIFICATION" como tag, coincidirá con el nombre "VERIFICATION_TEST_FILE"
        response = await file_search_tool.query_files(query, chat_id="TEST_USER", tags=["VERIFICATION"])
        
        print(f"Respuesta RAG: '{response}'")
        
        if "controlamos" in response or "opiniones" in response:
            print(" VERIFICACIÓN EXITOSA: La respuesta contiene información del archivo.")
        else:
            print(" VERIFICACIÓN PARCIAL: Respuesta recibida pero quizás no del archivo (o vacía).")

        # 5. Limpieza
        print("Limpiando archivo remoto...")
        await file_search_tool.delete_file(uploaded.name)
        print("Limpieza remota completa.")

    except Exception as e:
        print(f" ERROR CRÍTICO DURANTE VERIFICACIÓN: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if os.path.exists(dummy_file):
            os.remove(dummy_file)
            print("Archivo local eliminado.")

if __name__ == "__main__":
    asyncio.run(main())
