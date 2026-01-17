
import os
import google.generativeai as genai
from dotenv import load_dotenv

# Cargar entorno
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")

if not api_key:
    print("❌ Error: No se encontró GOOGLE_API_KEY o GEMINI_API_KEY en .env")
    exit(1)

genai.configure(api_key=api_key)

print("🔍 Buscando archivos en Google File API...")
try:
    files = list(genai.list_files())
    print(f"Total archivos encontrados: {len(files)}")

    for f in files:
        print(f"📄 {f.display_name} ({f.name}) - Estado: {f.state.name}")
        
        # Eliminar si falla o si el usuario quiere purgar todo (descomentar para purga total)
        # if True: 
        if f.state.name == "FAILED" or f.state.name == "PROCESSING":
            print(f"   🗑️ Eliminando archivo corrupto/atascado: {f.name}...")
            genai.delete_file(f.name)
            print("   ✅ Eliminado.")

    print("\n🏁 Diagnóstico finalizado.")

except Exception as e:
    print(f"❌ Error crítico al listar archivos: {e}")
