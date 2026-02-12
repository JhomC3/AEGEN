# tests/memory/test_knowledge_watcher.py
import asyncio
import os
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.memory.global_knowledge_loader import GlobalKnowledgeLoader
from src.memory.knowledge_watcher import KnowledgeWatcher


@pytest.mark.asyncio
async def test_knowledge_watcher_detection(tmp_path):
    """Prueba la detección de cambios (nuevo, modificado, eliminado)."""
    # Setup
    knowledge_dir = tmp_path / "knowledge"
    knowledge_dir.mkdir()

    # Mock loader
    loader = MagicMock(spec=GlobalKnowledgeLoader)
    loader.knowledge_path = knowledge_dir
    loader.ingest_file = AsyncMock(return_value=1)
    loader.manager = MagicMock()
    loader.manager.delete_file_knowledge = AsyncMock(return_value=1)
    loader._should_process_file = MagicMock(return_value=True)

    # Intervalo corto para el test
    watcher = KnowledgeWatcher(loader, interval=0.1)

    # Iniciar (sin archivos)
    await watcher.start()
    assert len(watcher._file_snapshots) == 0

    # 1. Prueba: Archivo Nuevo
    test_file = knowledge_dir / "test.txt"
    test_file.write_text("content")

    # Forzamos la comprobación manual para evitar sleeps largos
    await watcher._check_for_changes()

    loader.ingest_file.assert_awaited_once_with(test_file)
    assert "test.txt" in watcher._file_snapshots

    # 2. Prueba: Archivo Modificado
    loader.ingest_file.reset_mock()
    loader.manager.delete_file_knowledge.reset_mock()

    # Aseguramos que el mtime cambie (algunos sistemas tienen baja resolución)
    # En lugar de sleep, podemos forzar el mtime si fuera necesario,
    # pero write_text suele bastar en OS modernos.
    await asyncio.sleep(0.1)
    test_file.write_text("updated content")

    await watcher._check_for_changes()

    loader.manager.delete_file_knowledge.assert_awaited_with(
        "test.txt", namespace="global"
    )
    loader.ingest_file.assert_awaited_once_with(test_file)

    # 3. Prueba: Archivo Eliminado
    loader.ingest_file.reset_mock()
    loader.manager.delete_file_knowledge.reset_mock()

    os.remove(test_file)
    await watcher._check_for_changes()

    loader.manager.delete_file_knowledge.assert_awaited_once_with(
        "test.txt", namespace="global"
    )
    assert "test.txt" not in watcher._file_snapshots

    # Cleanup
    await watcher.stop()
