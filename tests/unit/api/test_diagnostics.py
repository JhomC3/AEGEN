# tests/unit/api/test_diagnostics.py
from unittest.mock import AsyncMock, patch

import pytest


class TestKnowledgeDiagnostics:
    """Verifica el endpoint de diagnóstico de conocimiento."""

    @pytest.mark.asyncio
    async def test_knowledge_status_returns_structure(self, async_client):
        """El endpoint debe retornar la estructura correcta."""
        with patch("src.api.routers.diagnostics.knowledge_auditor") as mock_auditor:
            mock_auditor.get_global_stats = AsyncMock(
                return_value={
                    "total_documents": 1,
                    "total_chunks": 100,
                    "last_sync": "2026-02-16T10:00:00",
                }
            )
            mock_auditor.get_knowledge_inventory = AsyncMock(
                return_value=[
                    {
                        "filename": "CORE_Test.pdf",
                        "chunk_count": 100,
                        "last_sync": "2026-02-16T10:00:00",
                    }
                ]
            )

            response = await async_client.get("/system/diagnostics/knowledge")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["total_documents"] == 1
            assert len(data["documents"]) == 1

    @pytest.mark.asyncio
    async def test_empty_knowledge_returns_empty_status(self, async_client):
        """Sin documentos, el status debe ser 'empty'."""
        with patch("src.api.routers.diagnostics.knowledge_auditor") as mock_auditor:
            mock_auditor.get_global_stats = AsyncMock(
                return_value={
                    "total_documents": 0,
                    "total_chunks": 0,
                    "last_sync": None,
                }
            )
            mock_auditor.get_knowledge_inventory = AsyncMock(return_value=[])

            response = await async_client.get("/system/diagnostics/knowledge")
            data = response.json()
            assert data["status"] == "empty"
