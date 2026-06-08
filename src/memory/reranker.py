# src/memory/reranker.py
import json
import logging
from typing import Any

from langchain_core.prompts import ChatPromptTemplate

logger = logging.getLogger(__name__)


class SemanticReranker:
    """
    Reranker semántico basado en llamadas ligeras a la API de Gemini.
    """

    def __init__(self) -> None:
        from src.core.llm_registry import get_llm

        self.llm = get_llm("rag_reranking")
        self.rerank_prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                (
                    "Eres un clasificador semántico de alta precisión. Tu tarea es evaluar la "
                    "relevancia de una lista de fragmentos recuperados en relación a la pregunta "
                    "actual del usuario. Devuelve únicamente un objeto JSON con el siguiente formato:\n"
                    '[{{"index": 0, "relevance": 0.95}}, {{"index": 1, "relevance": 0.12}}]\n'
                    "Donde 'index' es la posición del fragmento (0-indexed) y 'relevance' es un float de 0.0 a 1.0. "
                    "No incluyas explicaciones ni bloques Markdown de código, responde puramente con el JSON crudo."
                ),
            ),
            (
                "user",
                (
                    "PREGUNTA DEL USUARIO:\n{query}\n\n"
                    "LISTA DE FRAGMENTOS A EVALUAR:\n{fragments}\n\n"
                    "Clasifica y asigna el puntaje de relevancia a cada uno:"
                ),
            ),
        ])

    async def rerank(  # noqa: C901
        self, query: str, candidates: list[dict[str, Any]], top_k: int = 5
    ) -> list[dict[str, Any]]:
        """
        Ordena y filtra los candidatos semánticos en base a su relevancia.

        Args:
            query: Pregunta del usuario.
            candidates: Lista de fragmentos recuperados de SQLite.
            top_k: Número final de fragmentos a retornar.
        """
        if not candidates:
            return []

        # Si hay menos candidatos que el top_k, no es necesario llamar al LLM
        if len(candidates) <= top_k:
            return candidates

        logger.debug(
            f"[RERANKER] Evaluating {len(candidates)} candidates via Gemini API..."
        )

        # Preparar lista numerada para el prompt
        fragments_text = ""
        for idx, item in enumerate(candidates):
            fragments_text += f"Fragmento [{idx}]: {item.get('content', '')}\n---\n"

        try:
            chain = self.rerank_prompt | self.llm
            response = await chain.ainvoke({
                "query": query,
                "fragments": fragments_text,
            })

            # Sanitizar y parsear el JSON
            response_text = str(response.content).strip()
            if "```json" in response_text:
                response_text = (
                    response_text.split("```json")[1].split("```")[0].strip()
                )
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            scores = json.loads(response_text)
            if not isinstance(scores, list):
                raise ValueError("El formato retornado no es una lista JSON.")

            # Mapear scores y ordenar
            scored_candidates = []
            for item in scores:
                idx_raw = item.get("index")
                relevance = item.get("relevance", 0.0)
                if isinstance(idx_raw, int) and 0 <= idx_raw < len(candidates):
                    cand = candidates[idx_raw].copy()
                    cand["score"] = relevance
                    scored_candidates.append(cand)

            # Rellenar candidatos faltantes en caso de que el LLM omitiera alguno
            returned_indices = {
                item.get("index")
                for item in scores
                if isinstance(item.get("index"), int)
            }
            for idx, cand in enumerate(candidates):
                if idx not in returned_indices:
                    cand_copy = cand.copy()
                    # Penalizar levemente a los omitidos
                    cand_copy["score"] = cand_copy.get("score", 0.1) * 0.5
                    scored_candidates.append(cand_copy)

            # Ordenar por relevancia descendente
            scored_candidates.sort(key=lambda x: x.get("score", 0.0), reverse=True)
            logger.info(f"[RERANKER] Successful rerank. Truncating to Top-{top_k}.")
            return scored_candidates[:top_k]

        except Exception as e:
            logger.warning(
                f"[RERANKER] Failed semantic reranking: {e}. Falling back to default RRF order."
            )
            # Fallback seguro: retornar los candidatos originales truncados sin cambios
            return candidates[:top_k]
