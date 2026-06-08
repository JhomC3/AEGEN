#!/usr/bin/env python3
"""
CLI para gestión de conocimiento de AEGEN.

Uso:
    python scripts/knowledge_cli.py add <archivo> [--chunker semantic|recursive]
    python scripts/knowledge_cli.py sync [--chunker semantic|recursive]
    python scripts/knowledge_cli.py status
    python scripts/knowledge_cli.py delete <archivo>
    python scripts/knowledge_cli.py reingest [--chunker semantic|recursive]
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from src.core.config import settings
from src.memory.knowledge_manager import KnowledgeManager
from src.memory.knowledge_tracker import KnowledgeTracker
from src.memory.schemas.knowledge import KnowledgeChunker
from src.memory.sqlite_store import SQLiteStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("knowledge_cli")


async def _get_manager() -> tuple[KnowledgeManager, SQLiteStore]:
    """Inicializa store, tracker y manager."""
    store = SQLiteStore(settings.SQLITE_DB_PATH)
    await store.connect()
    await store.init_db(settings.SQLITE_SCHEMA_PATH)

    from src.memory.migration import apply_migrations

    await apply_migrations(store)

    tracker = KnowledgeTracker(store)
    manager = KnowledgeManager(store, tracker)
    return manager, store


async def cmd_add(args: argparse.Namespace) -> None:
    """Añade un archivo al sistema de conocimiento."""
    file_path = Path(args.file)
    chunker = KnowledgeChunker(args.chunker)

    manager, store = await _get_manager()
    try:
        result = await manager.add_file(file_path, chunker)
        if result.success:
            print(f"OK: {result.message}")
        else:
            print(f"ERROR: {result.message}")
            sys.exit(1)
    finally:
        await store.disconnect()


async def cmd_sync(args: argparse.Namespace) -> None:
    """Sincroniza storage/knowledge/ con el tracker."""
    chunker = KnowledgeChunker(args.chunker)

    manager, store = await _get_manager()
    try:
        results = await manager.sync_directory(chunker)
        if not results:
            print("Sin cambios. Todos los archivos ya están sincronizados.")
        else:
            ok = sum(1 for r in results if r.success)
            fail = sum(1 for r in results if not r.success)
            print(f"Sincronizados: {ok}, Errores: {fail}")
            for r in results:
                status = "OK" if r.success else "ERROR"
                print(f"  [{status}] {r.message}")
    finally:
        await store.disconnect()


async def cmd_status(args: argparse.Namespace) -> None:
    """Muestra estado de todos los archivos registrados."""
    manager, store = await _get_manager()
    try:
        status = await manager.get_status()
        print(f"Archivos: {status.total_files} | Chunks totales: {status.total_chunks}")
        print()

        if not status.files:
            print("No hay archivos registrados.")
            return

        # Header
        header = (
            f"{'Archivo':<35} {'Estado':<10} {'Chunker':<10} {'Chunks':<8} {'Hash':<16}"
        )
        print(header)
        print("-" * 85)

        for f in status.files:
            hash_short = f.file_hash[:12] + "..." if f.file_hash else "-"
            print(
                f"{f.filename:<35} {f.status.value:<10} "
                f"{f.chunker.value:<10} {f.chunks_count:<8} {hash_short:<16}"
            )
            if f.error_message:
                print(f"  Error: {f.error_message}")
    finally:
        await store.disconnect()


async def cmd_delete(args: argparse.Namespace) -> None:
    """Elimina un archivo y sus chunks."""
    manager, store = await _get_manager()
    try:
        success = await manager.delete_file(args.file)
        if success:
            print(f"OK: Archivo '{args.file}' eliminado.")
        else:
            print(f"ERROR: Archivo '{args.file}' no encontrado en el tracker.")
            sys.exit(1)
    finally:
        await store.disconnect()


async def cmd_reingest(args: argparse.Namespace) -> None:
    """Re-ingiere todos los archivos con el chunker especificado."""
    chunker = KnowledgeChunker(args.chunker)

    manager, store = await _get_manager()
    try:
        processed = await manager.reingest_all(chunker)
        print(f"Re-ingesta completada. Archivos procesados: {processed}")
    finally:
        await store.disconnect()


def main() -> None:
    parser = argparse.ArgumentParser(description="CLI de gestión de conocimiento AEGEN")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # add
    add_parser = subparsers.add_parser("add", help="Añadir archivo")
    add_parser.add_argument("file", help="Ruta al archivo")
    add_parser.add_argument(
        "--chunker",
        choices=["semantic", "recursive"],
        default="semantic",
        help="Chunker a usar (default: semantic)",
    )

    # sync
    sync_parser = subparsers.add_parser("sync", help="Sincronizar directorio")
    sync_parser.add_argument(
        "--chunker",
        choices=["semantic", "recursive"],
        default="semantic",
        help="Chunker a usar (default: semantic)",
    )

    # status
    subparsers.add_parser("status", help="Mostrar estado")

    # delete
    delete_parser = subparsers.add_parser("delete", help="Eliminar archivo")
    delete_parser.add_argument("file", help="Nombre del archivo")

    # reingest
    reingest_parser = subparsers.add_parser(
        "reingest", help="Re-ingestiar todos los archivos"
    )
    reingest_parser.add_argument(
        "--chunker",
        choices=["semantic", "recursive"],
        default="semantic",
        help="Chunker a usar (default: semantic)",
    )

    args = parser.parse_args()

    commands = {
        "add": cmd_add,
        "sync": cmd_sync,
        "status": cmd_status,
        "delete": cmd_delete,
        "reingest": cmd_reingest,
    }

    asyncio.run(commands[args.command](args))


if __name__ == "__main__":
    main()
