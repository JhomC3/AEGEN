# scripts/index_knowledge.py
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.tools.google_file_search import file_search_tool


async def index_directory(directory_path: str):
    """
    Sube todos los PDF y TXT de una carpeta a la Google File API.
    """
    path = Path(directory_path)
    if not path.exists():
        print(f"Directorio no encontrado: {directory_path}")
        return

    supported_extensions = [".pdf", ".txt", ".md"]
    files_to_upload = [
        f for f in path.iterdir() if f.suffix.lower() in supported_extensions
    ]

    if not files_to_upload:
        print("No se encontraron archivos compatibles (.pdf, .txt, .md)")
        return

    print(f"Encontrados {len(files_to_upload)} archivos. Iniciando subida...")

    for file_path in files_to_upload:
        try:
            print(f"Subiendo {file_path.name}...")
            # En la vida real, genai maneja el hashing para no subir duplicados exactos
            await file_search_tool.upload_file(str(file_path))
        except Exception as e:
            print(f"Error con {file_path.name}: {e}")

    print("\nProceso de indexación completado.")
    print("Archivos actuales en la Google File API:")
    files = await file_search_tool.list_files()
    for f in files:
        print(f"- {f.display_name} (URI: {f.uri}, Status: {f.state.name})")


if __name__ == "__main__":
    knowledge_dir = sys.argv[1] if len(sys.argv) > 1 else "knowledge"
    asyncio.run(index_directory(knowledge_dir))
