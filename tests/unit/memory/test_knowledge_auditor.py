# tests/unit/memory/test_knowledge_auditor.py
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.memory.knowledge_auditor import KnowledgeAuditor


class TestKnowledgeAuditor:
    """Verifica el auditor de conocimiento global."""

    @pytest.mark.asyncio
    async def test_get_knowledge_inventory_returns_list(self):
        """El inventario debe retornar una lista de documentos."""
        auditor = KnowledgeAuditor.__new__(KnowledgeAuditor)
        mock_store = MagicMock()
        mock_db = AsyncMock()
        mock_store.get_db = AsyncMock(return_value=mock_db)
        auditor._store = mock_store

        # Simular async context manager para db.execute
        mock_cursor = AsyncMock()
        mock_cursor.fetchall = AsyncMock(
            return_value=[
                {
                    "filename": "CORE_Test.pdf",
                    "chunk_count": 50,
                    "last_sync": "2026-02-16",
                },
            ]
        )

        # El execute debe retornar un objeto que sea async context manager
        # Y cuyo __aenter__ retorne el cursor
        execute_ctx = AsyncMock()
        execute_ctx.__aenter__.return_value = mock_cursor
        execute_ctx.__aexit__.return_value = None

        mock_db.execute = MagicMock(return_value=execute_ctx)

        result = await auditor.get_knowledge_inventory()
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["filename"] == "CORE_Test.pdf"
        assert result[0]["chunk_count"] == 50

    @pytest.mark.asyncio
    async def test_get_global_stats_structure(self):
        """Las estadísticas deben tener la estructura correcta."""
        auditor = KnowledgeAuditor.__new__(KnowledgeAuditor)
        mock_store = MagicMock()
        mock_db = AsyncMock()
        mock_store.get_db = AsyncMock(return_value=mock_db)
        auditor._store = mock_store

        mock_cursor = AsyncMock()
        mock_cursor.fetchone = AsyncMock(
            return_value={
                "total_documents": 2,
                "total_chunks": 847,
                "last_sync": "2026-02-16T10:30:00",
            }
        )

        execute_ctx = AsyncMock()
        execute_ctx.__aenter__.return_value = mock_cursor
        execute_ctx.__aexit__.return_value = None

        mock_db.execute = MagicMock(return_value=execute_ctx)

        result = await auditor.get_global_stats()
        assert "total_documents" in result
        assert "total_chunks" in result
        assert "last_sync" in result

    @pytest.mark.asyncio
    async def test_verify_document_retrievable(self):
        """La verificación debe hacer una búsqueda y confirmar resultados."""
        auditor = KnowledgeAuditor.__new__(KnowledgeAuditor)
        mock_manager = MagicMock()
        mock_manager.retrieve_context = AsyncMock(
            return_value=[
                {"id": 1, "content": "test", "metadata": {"filename": "CORE_Test.pdf"}},
            ]
        )
        auditor._manager = mock_manager

        result = await auditor.verify_document_retrievable(
            "CORE_Test.pdf", "protocolo unificado"
        )
        assert result["is_retrievable"] is True
        assert result["filename"] == "CORE_Test.pdf"
