# src/api/routers/diagnostics.py
"""
Endpoints de diagnóstico para observabilidad del conocimiento global (ADR-0025).
"""

import logging

from fastapi import APIRouter, Query

from src.core.schemas.api import KnowledgeDocumentStatus, KnowledgeStatusResponse
from src.memory.knowledge_auditor import knowledge_auditor

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get(
    "/knowledge",
    response_model=KnowledgeStatusResponse,
    tags=["Diagnostics"],
    summary="Estado del conocimiento global ingresado",
)
async def get_knowledge_status(
    verify: bool = Query(
        default=False,
        description="Ejecutar verificación de recuperabilidad semántica",
    ),
    sample_query: str = Query(
        default="protocolo terapéutico técnicas cognitivas",
        description="Query de prueba para verificación de recuperabilidad",
    ),
) -> KnowledgeStatusResponse:
    """
    Retorna el inventario completo del conocimiento global:
    documentos ingresados, cuenta de chunks, última sincronización.
    Opcionalmente verifica la recuperabilidad semántica de cada documento.
    """
    stats = await knowledge_auditor.get_global_stats()
    inventory = await knowledge_auditor.get_knowledge_inventory()

    documents = []
    for doc in inventory:
        doc_status = KnowledgeDocumentStatus(
            filename=doc["filename"],
            chunk_count=doc["chunk_count"],
            last_sync=doc["last_sync"],
        )

        if verify:
            verification = await knowledge_auditor.verify_document_retrievable(
                doc["filename"], sample_query
            )
            doc_status.is_retrievable = verification["is_retrievable"]

        documents.append(doc_status)

    # Estado global: healthy si hay documentos, warning si no
    status = "healthy" if stats["total_documents"] > 0 else "empty"
    if verify:
        all_retrievable = all(
            d.is_retrievable for d in documents if d.is_retrievable is not None
        )
        if not all_retrievable:
            status = "degraded"

    return KnowledgeStatusResponse(
        status=status,
        total_documents=stats["total_documents"],
        total_chunks=stats["total_chunks"],
        last_sync=stats["last_sync"],
        documents=documents,
    )
