# src/core/vector_memory_manager.py
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum

from src.core.session_manager import SessionManager
from src.vector_db.chroma_manager import ChromaManager

logger = logging.getLogger(__name__)


class MemoryType(str, Enum):
    """Tipos de memoria para contexto vectorial."""
    CONVERSATION = "conversation"
    DOCUMENT = "document"
    PREFERENCE = "preference"
    CONTEXT = "context"


class VectorMemoryManager:
    """Manager de memoria vectorial per-user que integra ChromaDB y Redis."""

    def __init__(
        self,
        chroma_manager: ChromaManager,
        session_manager: Optional[SessionManager] = None
    ):
        self.chroma_manager = chroma_manager
        self.session_manager = session_manager
        logger.info("VectorMemoryManager initialized")

    async def store_context(
        self,
        user_id: str,
        content: str,
        context_type: MemoryType = MemoryType.CONTEXT,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Almacena contexto persistente para el usuario."""
        try:
            data = {
                "content": content,
                "timestamp": datetime.utcnow().isoformat(),
                "context_type": context_type.value,
                **(metadata or {})
            }
            
            await self.chroma_manager.save_user_data(
                user_id=user_id,
                data=data,
                data_type=context_type.value
            )
            
            logger.info(f"Context stored for user {user_id}, type: {context_type}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store context for user {user_id}: {e}", exc_info=True)
            return False

    async def retrieve_context(
        self,
        user_id: str,
        query: str,
        context_type: Optional[MemoryType] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Recupera contexto relevante mediante búsqueda semántica."""
        try:
            results = await self.chroma_manager.query_user_data(
                user_id=user_id,
                query_text=query,
                data_type=context_type.value if context_type else None,
                n_results=limit
            )
            
            logger.info(f"Retrieved {len(results)} context items for user {user_id}")
            return results
            
        except Exception as e:
            logger.error(f"Failed to retrieve context for user {user_id}: {e}", exc_info=True)
            return []

    async def search_similar(
        self,
        user_id: str,
        content: str,
        threshold: float = 0.7,
        limit: int = 3
    ) -> List[Dict[str, Any]]:
        """Busca contenido similar en el contexto del usuario."""
        try:
            similar_results = await self.chroma_manager.query_user_data(
                user_id=user_id,
                query_text=content,
                n_results=limit
            )
            
            # Filtrar por threshold de similitud
            filtered_results = []
            for result in similar_results:
                distance = result.get("distance", 0)
                similarity = 1 - distance if distance is not None else 1.0
                
                if similarity >= threshold:
                    result["similarity_score"] = similarity
                    filtered_results.append(result)
            
            logger.info(f"Found {len(filtered_results)} similar items for user {user_id}")
            return filtered_results
            
        except Exception as e:
            logger.error(f"Failed to search similar content for user {user_id}: {e}", exc_info=True)
            return []