# src/memory/deduplicator.py
"""
Deduplication logic for memory ingestion.

Uses SHA-256 hashing to identify unique content.
"""

import hashlib
import logging

logger = logging.getLogger(__name__)


class Deduplicator:
    """
    Identifica contenido duplicado mediante hashes SHA-256.
    """

    @staticmethod
    def generate_hash(text: str) -> str:
        """
        Genera un hash SHA-256 determinista para un texto.
        Normaliza el texto (minúsculas, espacios extra) para mejor deduplicación.
        """
        if not text:
            return ""

        # Normalización básica
        normalized = " ".join(text.lower().split())
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    async def is_duplicate(self, text: str, existing_hashes: set[str]) -> bool:
        """
        Verifica si un texto ya existe en un conjunto de hashes.
        """
        content_hash = self.generate_hash(text)
        return content_hash in existing_hashes
