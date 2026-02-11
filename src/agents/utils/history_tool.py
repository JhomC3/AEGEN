from langchain_core.tools import tool

from src.core.dependencies import get_vector_memory_manager


@tool
async def query_user_history(chat_id: str, query: str) -> str:
    """
    5.2: Consulta el historial profundo del usuario para recuperar detalles del pasado.
    Útil para recordar metas, valores o eventos conversados hace mucho tiempo.
    """
    manager = get_vector_memory_manager()
    results = await manager.retrieve_context(user_id=chat_id, query=query, limit=5)

    if not results:
        return "No se encontraron detalles relevantes en el historial."

    context_parts = [f"[{r['created_at']}] {r['content']}" for r in results]
    return "\n\n".join(context_parts)
