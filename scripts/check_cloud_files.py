import asyncio
import logging
import sys
from pathlib import Path

# Añadir el directorio raíz al path para poder importar src
sys.path.append(str(Path(__file__).parent.parent))

from src.tools.google_file_search import file_search_tool

# Configurar logging mínimo para no ensuciar la salida
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger("check_cloud_files")


async def summarize_file(f, chat_id):
    """Obtiene un resumen corto del archivo usando RAG."""
    try:
        query = (
            "Resume brevemente el contenido de este archivo en una frase corta (máximo 15 palabras). "
            "Si es un perfil, dime el nombre del usuario. Si es conocimiento, el tema principal."
        )
        # Usamos query_files pero pasando directamente el archivo si pudiéramos,
        # pero la herramienta busca por chat_id y tags.
        # Vamos a usar una versión simplificada de la lógica de query_files.

        display_name = getattr(f, "display_name", "unknown")

        # Intentar determinar el chat_id del nombre del archivo si no se provee
        if not chat_id and "/" in display_name:
            chat_id = display_name.split("/")[0]

        summary = await file_search_tool.query_files(query, chat_id or "global")
        return summary or "Sin resumen disponible"
    except Exception:
        return "Error al generar resumen"


async def main():
    print("\n" + "=" * 80)
    print(f"{'INVENTARIO DE ARCHIVOS EN GOOGLE CLOUD':^80}")
    print("=" * 80 + "\n")

    print("Conectando con Google File API...")
    files = await file_search_tool.list_files()

    if not files:
        print("No se encontraron archivos en la nube.")
        return

    print(
        f"Se encontraron {len(files)} archivos. Generando resúmenes (esto puede tardar...)\n"
    )

    print(f"{'NOMBRE':<40} | {'TAMAÑO':<10} | {'RESUMEN'}")
    print("-" * 80)

    # Procesar archivos en paralelo para mayor velocidad, pero con un semáforo para no saturar la API
    semaphore = asyncio.Semaphore(3)  # Máximo 3 peticiones RAG simultáneas

    async def process_file(f):
        async with semaphore:
            display_name = getattr(f, "display_name", "unknown")
            size_kb = getattr(f, "size_bytes", 0) / 1024

            chat_id = None
            if "/" in display_name:
                chat_id = display_name.split("/")[0]

            summary = await summarize_file(f, chat_id)

            # Formatear salida
            name_str = (
                (display_name[:37] + "...") if len(display_name) > 40 else display_name
            )
            size_str = f"{size_kb:.1f} KB"
            print(f"{name_str:<40} | {size_str:<10} | {summary}")

    tasks = [process_file(f) for f in files]
    await asyncio.gather(*tasks)

    print("\n" + "=" * 80)
    print(f"{'FIN DEL REPORTE':^80}")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
