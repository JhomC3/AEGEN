# src/memory/semantic_chunker.py
import json
import logging
import re
from typing import Any

from langchain_core.prompts import ChatPromptTemplate

from src.core.engine import get_rag_llm

logger = logging.getLogger(__name__)

# Heurística para eliminar ruido común en transcripciones y documentos
RUIDO_PATTERNS = [
    re.compile(r"suscr\xedbete\s*al\s*canal", re.IGNORECASE),
    re.compile(r"subscribe\s*to\s*the\s*channel", re.IGNORECASE),
    re.compile(r"eh+\s*,\s*eh+", re.IGNORECASE),
    re.compile(r"^\s*eh+\s*$", re.IGNORECASE),
    re.compile(r"^\s*uh+\s*$", re.IGNORECASE),
    re.compile(r"\b\d{2}:\d{2}:\d{2}\b"),  # timestamps de videos
    re.compile(r"\b\d{2}:\d{2}\b"),
]


class SemanticChunker:
    """
    Chunker semántico que purifica texto crudo y delega al LLM (Gemini Flash)
    para segmentar en bloques Nivel 3 (marcos/conceptos) y Nivel 4 (hechos atómicos).
    """

    def __init__(self) -> None:
        self.llm = get_rag_llm()
        self.chunking_prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                (
                    "Eres un catalogador semántico de información clínica e investigativa. "
                    "Tu tarea es dividir un texto extenso purificado en bloques lógicos o capítulos "
                    "de marco teórico (Nivel 3) y, a partir de ellos, extraer pequeños fragmentos "
                    "precisos y coherentes (Nivel 4) con su correspondiente clasificación de dominio.\n"
                    "Dominios válidos: 'psychology', 'finance', 'fitness', 'nutrition', 'general'.\n"
                    "Responde estrictamente con un objeto JSON con la lista estructurada jerárquicamente:\n"
                    "{\n"
                    '  "chunks": [\n'
                    "    {\n"
                    '      "content": "Concepto o Marco Macro (Nivel 3)",\n'
                    '      "domain": "psychology",\n'
                    '      "children": [\n'
                    '        {"content": "Detalle preciso o técnica 1 (Nivel 4)", "domain": "psychology"},\n'
                    '        {"content": "Detalle preciso o técnica 2 (Nivel 4)", "domain": "psychology"}\n'
                    "      ]\n"
                    "    }\n"
                    "  ]\n"
                    "}\n"
                    "No incluyas explicaciones, responde puramente con el JSON crudo."
                ),
            ),
            (
                "user",
                (
                    "TEXTO PURIFICADO A SEGMENTAR:\n{text}\n\n"
                    "Segmenta jerárquicamente en bloques Nivel 3 y 4:"
                ),
            ),
        ])

    def clean_noise(self, text: str) -> str:
        """Purifica el texto aplicando stop-words y filtros heurísticos contra ruido."""
        if not text:
            return ""

        lines = text.split("\n")
        cleaned_lines = []

        for line in lines:
            # Filtrar patrones de ruido
            match_noise = False
            for pattern in RUIDO_PATTERNS:
                if pattern.search(line):
                    match_noise = True
                    break

            if not match_noise and line.strip():
                cleaned_lines.append(line.strip())

        return "\n".join(cleaned_lines)

    async def chunk_semantically(self, text: str) -> list[dict[str, Any]]:
        """
        Limpia el texto y realiza la llamada a Gemini para segmentación semántica.
        Retorna una lista plana de chunks con su jerarquía parent_id resuelta.
        """
        purified = self.clean_noise(text)
        if not purified:
            return []

        logger.debug(
            "[SEMANTIC-CHUNKER] Sending purified text to Gemini Flash for chunking..."
        )

        try:
            chain = self.chunking_prompt | self.llm
            response = await chain.ainvoke({
                "text": purified[:8000]
            })  # Truncar a 8k caracteres para safety

            response_text = str(response.content).strip()
            if "```json" in response_text:
                response_text = (
                    response_text.split("```json")[1].split("```")[0].strip()
                )
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            data = json.loads(response_text)
            chunks_structure = data.get("chunks", [])

            flat_results = []
            for item in chunks_structure:
                parent_content = item.get("content")
                parent_domain = item.get("domain", "general")
                if not parent_content:
                    continue

                # Guardamos la estructura Nivel 3
                parent_chunk = {
                    "content": parent_content,
                    "hierarchy_level": 3,
                    "domain": parent_domain,
                    "children": [],
                }

                # Añadimos los hijos Nivel 4
                children_list = item.get("children", [])
                for child in children_list:
                    child_content = child.get("content")
                    child_domain = child.get("domain", parent_domain)
                    if child_content:
                        parent_chunk["children"].append({
                            "content": child_content,
                            "hierarchy_level": 4,
                            "domain": child_domain,
                        })

                flat_results.append(parent_chunk)

            return flat_results

        except Exception as e:
            logger.warning(
                f"[SEMANTIC-CHUNKER] Failed semantic chunking: {e}. Falling back to empty structure."
            )
            return []
