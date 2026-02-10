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

    Estrategia:
    1. Intentar dividir por párrafos (\n\n)
    2. Si un párrafo es muy grande, dividir por oraciones (. ! ?)
    3. Si una oración es muy grande, dividir por palabras
    4. Mantener overlap para preservar contexto
    """

    def __init__(
        self,
        chunk_size: int = 400,
        chunk_overlap: int = 80,
        encoding_name: str = "cl100k_base",  # GPT-4/text-embedding-004
    ):
        """
        Args:
            chunk_size: Tamaño máximo del chunk en tokens
            chunk_overlap: Tokens de solapamiento entre chunks
            encoding_name: Tokenizer de tiktoken a usar
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.encoding = tiktoken.get_encoding(encoding_name)

        # Separadores en orden de prioridad (más específico → más general)
        self.separators = [
            "\n\n",  # Párrafos
            "\n",  # Líneas
            ". ",  # Oraciones (punto + espacio)
            "! ",  # Exclamaciones
            "? ",  # Preguntas
            "; ",  # Punto y coma
            ", ",  # Comas
            " ",  # Palabras
            "",  # Caracteres (último recurso)
        ]

    def count_tokens(self, text: str) -> int:
        """Cuenta tokens usando tiktoken."""
        return len(self.encoding.encode(text))

    def chunk(self, text: str, metadata: dict | None = None) -> list[Chunk]:
        """
        Divide el texto en chunks recursivamente.

        Args:
            text: Texto a dividir
            metadata: Metadatos adicionales para cada chunk

        Returns:
            Lista de Chunks con solapamiento
        """
        if not text or not text.strip():
            return []

        metadata = metadata or {}
        chunks = []

        # Dividir recursivamente
        splits = self._recursive_split(text)

        # Crear chunks con overlap
        current_chunk: list[str] = []
        current_length = 0

        for split in splits:
            split_tokens = self.count_tokens(split)

            # Si el split solo ya excede el tamaño, lo añadimos directamente
            if split_tokens > self.chunk_size:
                if current_chunk:
                    # Guardar chunk actual
                    chunk_text = "".join(current_chunk)
                    chunks.append(
                        Chunk(
                            content=chunk_text,
                            start_index=0,  # TODO: calcular índices reales
                            end_index=len(chunk_text),
                            metadata={
                                **metadata,
                                "tokens": self.count_tokens(chunk_text),
                            },
                        )
                    )
                    current_chunk = []
                    current_length = 0

                # Añadir el split grande como un chunk individual
                chunks.append(
                    Chunk(
                        content=split,
                        start_index=0,
                        end_index=len(split),
                        metadata={
                            **metadata,
                            "tokens": split_tokens,
                            "oversized": True,
                        },
                    )
                )
                continue

            # Si añadir este split excede el límite
            if current_length + split_tokens > self.chunk_size:
                # Guardar chunk actual
                chunk_text = "".join(current_chunk)
                chunks.append(
                    Chunk(
                        content=chunk_text,
                        start_index=0,
                        end_index=len(chunk_text),
                        metadata={**metadata, "tokens": self.count_tokens(chunk_text)},
                    )
                )

                # Calcular overlap
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

                # Iniciar nuevo chunk con overlap
                current_chunk = overlap_chunks
                current_length = overlap_tokens

            # Añadir split al chunk actual
            current_chunk.append(split)
            current_length += split_tokens

        # Guardar último chunk si existe
        if current_chunk:
            chunk_text = "".join(current_chunk)
            chunks.append(
                Chunk(
                    content=chunk_text,
                    start_index=0,
                    end_index=len(chunk_text),
                    metadata={**metadata, "tokens": self.count_tokens(chunk_text)},
                )
            )

        logger.info(
            f"Chunked text into {len(chunks)} chunks "
            f"(avg {sum(c.metadata['tokens'] for c in chunks) / len(chunks):.0f} tokens/chunk)"
        )

        return chunks

    def _recursive_split(self, text: str, separator_index: int = 0) -> list[str]:
        """
        Divide texto recursivamente usando separadores en orden de prioridad.

        Args:
            text: Texto a dividir
            separator_index: Índice del separador actual en self.separators

        Returns:
            Lista de fragmentos de texto
        """
        if separator_index >= len(self.separators):
            return [text] if text else []

        separator = self.separators[separator_index]

        # Si no hay separador (último recurso), dividir por caracteres
        if separator == "":
            # Dividir en chunks del tamaño exacto de tokens
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

            # Si el split es demasiado grande, dividirlo recursivamente con el siguiente separador
            if self.count_tokens(split) > self.chunk_size:
                result.extend(self._recursive_split(split, separator_index + 1))
            else:
                result.append(split)

        return result
