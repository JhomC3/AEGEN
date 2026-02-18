#!/usr/bin/env python3
# scripts/archive_legacy.py
"""
Script de limpieza física de la base de conocimientos.

Mueve archivos personales legacy (JSON, TXT con IDs) de 'storage/knowledge/'
a 'storage/archive/' para mantener el directorio de conocimiento limpio.

Uso: python scripts/archive_legacy.py
"""

import re
import shutil
from pathlib import Path

# Configuración de rutas
BASE_DIR = Path(__file__).parent.parent
KNOWLEDGE_DIR = BASE_DIR / "storage" / "knowledge"
ARCHIVE_DIR = BASE_DIR / "storage" / "archive"


def should_archive(file_path: Path) -> bool:
    """Determina si un archivo es legacy/personal y debe ser archivado."""
    name = file_path.name.lower()

    # 1. Archivos con IDs de usuario (números largos)
    if re.search(r"\d{5,}", name):
        return True

    # 2. Palabras clave de archivos personales legacy
    ignore_keywords = ("buffer", "summary", "vault", "profile", "knowledge_loader")
    return bool(
        any(kw in name for kw in ignore_keywords)
        and file_path.suffix.lower() in (".json", ".txt")
    )


def main():
    print("=== Iniciando Limpieza de Conocimiento Legacy ===")

    if not KNOWLEDGE_DIR.exists():
        print(f"Error: No se encontró el directorio {KNOWLEDGE_DIR}")
        return

    # Asegurar que el directorio de archivo existe
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    archived_count = 0

    for file_path in KNOWLEDGE_DIR.glob("*"):
        if file_path.is_dir() or file_path.name.startswith("."):
            continue

        # No archivar documentos CORE
        if "CORE" in file_path.name or "Unified Protocol" in file_path.name:
            continue

        if should_archive(file_path):
            dest_path = ARCHIVE_DIR / file_path.name
            print(f"Archivando: {file_path.name} -> storage/archive/")

            try:
                # Usar move para evitar duplicados
                shutil.move(str(file_path), str(dest_path))
                archived_count += 1
            except Exception as e:
                print(f"Error moviendo {file_path.name}: {e}")

    print(f"=== Limpieza completada. Archivos movidos: {archived_count} ===")


if __name__ == "__main__":
    main()
