# src/memory/schemas/knowledge.py
"""
Esquemas Pydantic para el sistema de gestión de conocimiento de AEGEN.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class KnowledgeStatus(str, Enum):
    """Estados posibles de un archivo de conocimiento."""

    PENDING = "pending"
    INGESTING = "ingesting"
    DONE = "done"
    FAILED = "failed"


class KnowledgeChunker(str, Enum):
    """Chunkers disponibles para ingestión."""

    SEMANTIC = "semantic"
    RECURSIVE = "recursive"


class KnowledgeFile(BaseModel):
    """Representa un archivo de conocimiento registrado en el tracker."""

    id: int = Field(default=0)
    filename: str
    file_hash: str
    file_size: int
    status: KnowledgeStatus = KnowledgeStatus.PENDING
    chunker: KnowledgeChunker = KnowledgeChunker.SEMANTIC
    chunks_count: int = 0
    chunks_ids: list[int] = Field(default_factory=list)
    ingested_at: datetime | None = None
    updated_at: datetime = Field(default_factory=datetime.now)
    error_message: str | None = None


class KnowledgeStatusResponse(BaseModel):
    """Respuesta del estado del sistema de conocimiento."""

    total_files: int
    total_chunks: int
    files: list[KnowledgeFile]


class KnowledgeAddResponse(BaseModel):
    """Respuesta al añadir un archivo."""

    success: bool
    file: KnowledgeFile | None = None
    message: str
