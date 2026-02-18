# src/memory/knowledge_auditor.py
"""
Auditor de conocimiento global (ADR-0025).

Provee inventario, estadísticas y verificación bajo demanda
del conocimiento almacenado en el namespace 'global'.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class KnowledgeAuditor:
    """
    Audita el estado del conocimiento global almacenado en SQLite.
    Verificación de recuperabilidad solo bajo demanda.
    """

    def __init__(self):
        self._store = None
        self._manager = None

    @property
    def store(self):
        """Lazy load del SQLiteStore."""
        if self._store is None:
            from src.core.dependencies import get_sqlite_store

            self._store = get_sqlite_store()
        return self._store

    @property
    def manager(self):
        """Lazy load del VectorMemoryManager."""
        if self._manager is None:
            from src.core.dependencies import get_vector_memory_manager

            self._manager = get_vector_memory_manager()
        return self._manager

    async def get_knowledge_inventory(self) -> list[dict[str, Any]]:
        """
        Retorna el inventario de documentos globales con estadísticas.
        """
        db = await self.store.get_db()
        query = """
            SELECT
                json_extract(metadata, '$.filename') as filename,
                COUNT(*) as chunk_count,
                MAX(created_at) as last_sync
            FROM memories
            WHERE namespace = 'global' AND is_active = 1
            GROUP BY json_extract(metadata, '$.filename')
            ORDER BY last_sync DESC
        """
        results = []
        async with db.execute(query) as cursor:
            rows = await cursor.fetchall()
            for row in rows:
                results.append({
                    "filename": row["filename"],
                    "chunk_count": row["chunk_count"],
                    "last_sync": row["last_sync"],
                })
        return results

    async def get_global_stats(self) -> dict[str, Any]:
        """Retorna estadísticas globales del conocimiento."""
        db = await self.store.get_db()
        query = """
            SELECT
                COUNT(DISTINCT json_extract(metadata, '$.filename'))
                    as total_documents,
                COUNT(*) as total_chunks,
                MAX(created_at) as last_sync
            FROM memories
            WHERE namespace = 'global' AND is_active = 1
        """
        async with db.execute(query) as cursor:
            row = await cursor.fetchone()
            return {
                "total_documents": row["total_documents"] or 0,
                "total_chunks": row["total_chunks"] or 0,
                "last_sync": row["last_sync"],
            }

    async def verify_document_retrievable(
        self, filename: str, sample_query: str
    ) -> dict[str, Any]:
        """
        Verifica que un documento es recuperable via búsqueda semántica.
        Ejecuta una query de prueba y verifica coincidencia de fuente.
        """
        results = await self.manager.retrieve_context(
            user_id="system",
            query=sample_query,
            limit=5,
            namespace="global",
        )

        found = any(r.get("metadata", {}).get("filename") == filename for r in results)

        logger.info(
            f"[AUDITOR] Verificación de '{filename}': "
            f"{'recuperable' if found else 'NO recuperable'} "
            f"(query: '{sample_query[:50]}...')"
        )

        return {
            "filename": filename,
            "is_retrievable": found,
            "query_used": sample_query[:80],
            "results_returned": len(results),
        }


# Singleton
knowledge_auditor = KnowledgeAuditor()
