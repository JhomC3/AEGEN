# src/memory/chunker.py
"""
Recursive text chunker for memory ingestion.

Divide texto en fragmentos óptimos de 400 tokens con overlap de 80,
utilizando divisiones naturales (párrafos → oraciones → palabras).
"""

import logging
from dataclasses import dataclass

import tiktoken

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """Representa un fragmento de texto con metadatos."""

    content: str
    start_index: int
    end_index: int
    metadata: dict


class RecursiveChunker:
    """
    Chunker recursivo que divide texto en fragmentos optimizados para embeddings.
    """

    def __init__(
        self,
        chunk_size: int = 400,
        chunk_overlap: int = 80,
        encoding_name: str = "cl100k_base",
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.encoding = tiktoken.get_encoding(encoding_name)

        # Separadores en orden de prioridad
        self.separators = [
            "\n\n",  # Párrafos
            "\n",  # Líneas
            ". ",  # Oraciones
            "! ",  # Exclamaciones
            "? ",  # Preguntas
            "; ",  # Punto y coma
            ", ",  # Comas
            " ",  # Palabras
            "",  # Caracteres
        ]

    def count_tokens(self, text: str) -> int:
        """Cuenta tokens usando tiktoken."""
        return len(self.encoding.encode(text))

    def _create_chunk(self, content: str, metadata: dict) -> Chunk:
        """Crea un objeto Chunk con metadatos."""
        return Chunk(
            content=content,
            start_index=0,  # TODO: calcular índices reales
            end_index=len(content),
            metadata={
                **metadata,
                "tokens": self.count_tokens(content),
            },
        )

    def _calculate_overlap(self, current_chunk: list[str]) -> tuple[list[str], int]:
        """Calcula el overlap para el siguiente chunk."""
        overlap_chunks: list[str] = []
        overlap_tokens = 0

        # Tomar los últimos elementos hasta completar el overlap
        for i in range(len(current_chunk) - 1, -1, -1):
            piece = current_chunk[i]
            piece_tokens = self.count_tokens(piece)

            if overlap_tokens + piece_tokens <= self.chunk_overlap:
                overlap_chunks.insert(0, piece)
                overlap_tokens += piece_tokens
            else:
                break
        return overlap_chunks, overlap_tokens

    def chunk(self, text: str, metadata: dict | None = None) -> list[Chunk]:
        """
        Divide el texto en chunks recursivamente.
        """
        if not text or not text.strip():
            return []

        metadata = metadata or {}
        chunks = []
        splits = self._recursive_split(text)

        current_chunk: list[str] = []
        current_length = 0

        for split in splits:
            split_tokens = self.count_tokens(split)

            # Si el split solo ya excede el tamaño
            if split_tokens > self.chunk_size:
                if current_chunk:
                    chunks.append(self._create_chunk("".join(current_chunk), metadata))
                    current_chunk = []
                    current_length = 0

                # Añadir split grande como chunk individual
                # Usamos _create_chunk pero marcamos oversized en metadata
                large_chunk = self._create_chunk(split, metadata)
                large_chunk.metadata["oversized"] = True
                chunks.append(large_chunk)
                continue

            # Si añadir este split excede el límite
            if current_length + split_tokens > self.chunk_size:
                chunks.append(self._create_chunk("".join(current_chunk), metadata))

                # Iniciar nuevo chunk con overlap
                current_chunk, current_length = self._calculate_overlap(current_chunk)

            # Añadir split al chunk actual
            current_chunk.append(split)
            current_length += split_tokens

        # Guardar último chunk
        if current_chunk:
            chunks.append(self._create_chunk("".join(current_chunk), metadata))

        logger.info(
            f"Chunked text into {len(chunks)} chunks "
            f"(avg {sum(c.metadata['tokens'] for c in chunks) / len(chunks):.0f} tokens/chunk)"
        )

        return chunks

    def _recursive_split(self, text: str, separator_index: int = 0) -> list[str]:
        """
        Divide texto recursivamente usando separadores en orden de prioridad.
        """
        if separator_index >= len(self.separators):
            return [text] if text else []

        separator = self.separators[separator_index]

        # Si no hay separador (último recurso), dividir por caracteres
        if separator == "":
            splits = []
            current = ""
            for char in text:
                current += char
                if self.count_tokens(current) >= self.chunk_size:
                    splits.append(current)
                    current = ""
            if current:
                splits.append(current)
            return splits

        # Dividir por el separador actual
        splits = text.split(separator)

        # Re-añadir el separador excepto al final
        if separator:
            splits = [
                split + separator if i < len(splits) - 1 else split
                for i, split in enumerate(splits)
            ]

        # Procesar cada split
        result = []
        for split in splits:
            if not split:
                continue

            # Si el split es demasiado grande, dividirlo recursivamente
            if self.count_tokens(split) > self.chunk_size:
                result.extend(self._recursive_split(split, separator_index + 1))
            else:
                result.append(split)

        return result
