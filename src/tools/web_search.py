# src/tools/web_search.py
"""
Web Search Tool — Busqueda en internet via DuckDuckGo.

Permite a MAGI buscar informacion actualizada en tiempo real.
"""

import logging

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


async def _search_web(query: str, max_results: int = 5) -> list[dict]:
    """
    Busca en la web usando DuckDuckGo.

    Args:
        query: Terminos de busqueda.
        max_results: Maximo de resultados.

    Returns:
        Lista de resultados con title, snippet, url.
    """
    try:
        from duckduckgo_search import DDGS

        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))

        return [
            {
                "title": r.get("title", ""),
                "snippet": r.get("body", ""),
                "url": r.get("href", ""),
            }
            for r in results
        ]
    except ImportError:
        logger.warning(
            "[WEB-SEARCH] duckduckgo-search no instalado. pip install duckduckgo-search"
        )
        return []
    except Exception as e:
        logger.warning("[WEB-SEARCH] Error en busqueda: %s", e)
        return []


def _format_results(results: list[dict]) -> str:
    """Formatea resultados de busqueda para el prompt."""
    if not results:
        return "No encontre resultados relevantes en la busqueda."

    lines = [f"Encontre {len(results)} resultado(s):\n"]
    for i, r in enumerate(results, 1):
        lines.append(f"{i}. **{r['title']}**")
        lines.append(f"   {r['snippet'][:200]}")
        lines.append(f"   URL: {r['url']}")
        lines.append("")

    return "\n".join(lines)


@tool
async def search_web(query: str, max_results: int = 5) -> str:
    """
    Busca informacion actualizada en internet.

    Usar cuando el usuario pregunta sobre eventos recientes,
    noticias, datos actualizados o informacion que no esta
    en el conocimiento almacenado.

    Args:
        query: Terminos de busqueda.
        max_results: Maximo de resultados (default: 5).

    Returns:
        Resultados formateados como texto.
    """
    try:
        results = await _search_web(query, max_results)
        return _format_results(results)
    except Exception as e:
        logger.warning("[WEB-SEARCH] Error: %s", e)
        return "No pude realizar la busqueda en este momento."
