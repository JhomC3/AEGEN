import logging
from typing import Any, Dict, List, Literal, Optional

import chromadb
from chromadb.utils import embedding_functions

logger = logging.getLogger(__name__)


class ChromaManager:
    """Manages ChromaDB with user isolation via separate collections."""

    def __init__(self, client: chromadb.HttpClient, embedding_function: Any):
        """
        Initialize ChromaManager with dependency injection.
        
        Args:
            client: Async ChromaDB HttpClient
            embedding_function: Embedding function for collections
        """
        self.logger = logging.getLogger(__name__)
        self.client = client
        self.embedding_function = embedding_function
        self.logger.info("ChromaManager initialized with injected dependencies")

    async def _get_user_collection(self, user_id: str):
        """Gets or creates isolated collection for user."""
        safe_user_id = str(user_id).replace("-", "_").replace(".", "_")
        collection_name = f"user_{safe_user_id}"
        
        try:
            collection = await self.client.get_or_create_collection(
                name=collection_name,
                embedding_function=self.embedding_function,  # type: ignore[arg-type]
            )
            self.logger.debug(f"User collection '{collection_name}' ready")
            return collection
        except Exception as e:
            self.logger.error(f"Failed to get user collection '{collection_name}': {e}")
            raise

    async def save_user_data(
        self, 
        user_id: str, 
        data: Dict[str, Any], 
        data_type: Literal["conversation", "document", "preference"] = "conversation"
    ) -> None:
        """Saves data to user-specific collection."""
        try:
            user_collection = await self._get_user_collection(user_id)
            
            doc_id = str(data.get("message_id") or hash(data.get("content", "")))
            document_text = data.get("content") or data.get("transcript", "")

            if not document_text:
                self.logger.warning(f"No content for user {user_id}, doc_id: {doc_id}")
                return

            metadata = {**data, "data_type": data_type}

            await user_collection.add(
                ids=[doc_id],
                documents=[document_text],
                metadatas=[metadata],
            )
            self.logger.info(f"Saved to user_{user_id} collection")
        except Exception as e:
            self.logger.error(f"Failed to save user data for {user_id}: {e}")
            raise

    async def query_user_data(
        self, 
        user_id: str, 
        query_text: str, 
        data_type: Optional[str] = None,
        n_results: int = 5
    ) -> List[Dict[str, Any]]:
        """Queries data from user-specific collection only."""
        try:
            user_collection = await self._get_user_collection(user_id)
            
            where_clause = {"data_type": data_type} if data_type else None

            results = await user_collection.query(
                query_texts=[query_text],
                n_results=n_results,
                where=where_clause,
            )
            
            processed_results = []
            if results["documents"] and results["documents"][0]:
                for i, doc in enumerate(results["documents"][0]):
                    processed_results.append({
                        "document": doc,
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                        "distance": results["distances"][0][i] if results.get("distances") else 0,
                        "id": results["ids"][0][i] if results["ids"] else "",
                    })
            
            return processed_results
        except Exception as e:
            self.logger.error(f"Failed to query user data for {user_id}: {e}")
            raise
