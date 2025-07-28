import logging

import chromadb
from chromadb.utils import embedding_functions

logger = logging.getLogger(__name__)


class ChromaManager:
    """
    Gestiona la conexión y las operaciones con la base de datos vectorial ChromaDB.
    """

    def __init__(self, collection_name: str = "telegram_data"):
        self.logger = logging.getLogger(__name__)
        try:
            self.logger.info("Initializing connection to ChromaDB...")
            # Aquí puedes configurar para usar ChromaDB en la nube o local
            self.client = chromadb.Client()  # O chromadb.CloudClient(...)

            # Usar una función de embedding por defecto o una más avanzada
            embedding_function = embedding_functions.DefaultEmbeddingFunction()

            self.collection = self.client.get_or_create_collection(
                name=collection_name,
                embedding_function=embedding_function,
            )
            self.logger.info(
                f"ChromaDB connection established. Collection '{collection_name}' is ready."
            )
        except Exception as e:
            self.logger.critical(f"Failed to connect to ChromaDB: {e}", exc_info=True)
            raise

    async def save(self, data: dict):
        """
        Guarda un documento en la colección de ChromaDB.
        El 'id' del documento será su 'message_id' o un hash del contenido.
        El 'document' será el texto a indexar.
        El 'metadata' será el resto de la información.
        """
        try:
            doc_id = str(data.get("message_id") or hash(data.get("content", "")))
            document_text = data.get("content") or data.get("transcript", "")

            if not document_text:
                self.logger.warning(
                    f"No content to save for doc_id: {doc_id}. Skipping."
                )
                return

            self.logger.info(f"Saving document to ChromaDB with id: {doc_id}")
            self.collection.add(
                ids=[doc_id],
                documents=[document_text],
                metadatas=[data],
            )
        except Exception as e:
            self.logger.error(f"Error saving document to ChromaDB: {e}", exc_info=True)

    # Aquí podrías añadir más métodos como query, delete, etc.
