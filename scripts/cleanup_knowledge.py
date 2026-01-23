import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.tools.google_file_search import file_search_tool


async def cleanup_duplicates():
    print("--- Iniciando Limpieza de Duplicados en Google File API ---")
    files = await file_search_tool.list_files()

    if not files:
        print("No se encontraron archivos.")
        return

    # Agrupar por nombre para identificar duplicados
    seen = {}
    to_delete = []

    # Ordenar por fecha de creación (los más recientes primero si es posible,
    # pero el SDK no siempre lo da directo, así que usaremos el orden de la lista
    # que suele ser cronológico inverso o directo)
    for f in files:
        name = f.display_name
        if name in seen:
            # Es un duplicado, lo marcamos para borrar
            to_delete.append(f)
        else:
            seen[name] = f

    if not to_delete:
        print("✅ No se encontraron duplicados. Todo limpio.")
        return

    print(f"Se encontraron {len(to_delete)} archivos duplicados.")
    for f in to_delete:
        try:
            print(f"Eliminando duplicado: {f.display_name} ({f.name})")
            await file_search_tool.delete_file(f.name)
        except Exception as e:
            print(f"Error eliminando {f.display_name}: {e}")

    print("\n--- Limpieza completada ---")
    print("Archivos restantes:")
    remaining = await file_search_tool.list_files()
    for f in remaining or []:
        print(f"- {f.display_name} (Status: {f.state.name})")


if __name__ == "__main__":
    asyncio.run(cleanup_duplicates())
