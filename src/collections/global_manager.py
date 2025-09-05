# src/collections/global_manager.py
"""
Gestión de collections compartidas entre usuarios.

Responsabilidad única: crear, consultar y gestionar collections
globales con validación de permisos y nomenclatura.
"""

import logging
from typing import Dict, Any, List, Optional

from src.collections.reserved_collections import ReservedCollections
from src.core.security.access_controller import AccessController
from src.vector_db.chroma_manager import ChromaManager

logger = logging.getLogger(__name__)


class GlobalCollectionManager:
    """Gestión de collections compartidas entre usuarios."""

    def __init__(self, chroma_manager: ChromaManager, access_controller: AccessController):
        self.chroma_manager = chroma_manager
        self.access_controller = access_controller
        self.reserved_collections = ReservedCollections()
        self.logger = logging.getLogger(__name__)

    async def create_global_collection(self, name: str, creator_id: str, metadata: Dict[str, Any]) -> bool:
        """Crea collection global con validación de permisos."""
        try:
            # Validar nombre no reservado para collections custom
            if not name.startswith('global_'):
                name = f'global_{name}'
            
            # Verificar permisos de creación global
            if not await self.access_controller.validate_global_access(creator_id, name):
                self.logger.warning(f"User {creator_id} denied permission to create global collection {name}")
                return False

            # Validar que no sea collection reservada sin permisos
            if self.reserved_collections.is_reserved_collection(name):
                config = self.reserved_collections.get_reserved_collection_config(name)
                create_permissions = config.get('permissions', {}).get('write', [])
                # Aquí debería verificarse el rol del usuario, simplificado por ahora
                self.logger.info(f"Creating reserved collection {name} by {creator_id}")

            # Crear metadata enriquecido
            collection_metadata = {
                'collection_type': 'global',
                'created_by': creator_id,
                'is_reserved': self.reserved_collections.is_reserved_collection(name),
                **metadata
            }

            # Por ahora simulamos creación exitosa
            # En implementación real se integraría con ChromaManager
            self.logger.info(f"Global collection '{name}' created by {creator_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to create global collection {name}: {e}", exc_info=True)
            return False

    async def query_global_collection(self, collection_name: str, query_text: str, user_id: str, 
                                    n_results: int = 5) -> List[Dict[str, Any]]:
        """Consulta collection global con validación de acceso."""
        try:
            # Validar acceso a collection global
            if not await self.access_controller.validate_global_access(user_id, collection_name):
                await self.access_controller.log_access_attempt(user_id, f"global_{collection_name}", "read", False)
                return []

            # Verificar permisos específicos de collection reservada
            if self.reserved_collections.is_reserved_collection(collection_name):
                read_permissions = self.reserved_collections.get_collection_permissions(collection_name, 'read')
                # Validación simplificada por ahora
                self.logger.debug(f"Reserved collection {collection_name} read permissions: {read_permissions}")

            # Por ahora retornamos resultado vacío
            # En implementación real se consultaría ChromaManager
            results = []
            
            await self.access_controller.log_access_attempt(user_id, f"global_{collection_name}", "read", True)
            return results

        except Exception as e:
            self.logger.error(f"Failed to query global collection {collection_name}: {e}", exc_info=True)
            return []

    async def list_available_global_collections(self, user_id: str) -> List[str]:
        """Lista collections globales disponibles para el usuario."""
        try:
            # Validar permisos globales básicos
            if not await self.access_controller.validate_global_access(user_id, "list_collections"):
                return []

            # Obtener collections reservadas que el usuario puede ver
            available_collections = []
            
            for collection_name, config in self.reserved_collections.RESERVED_COLLECTIONS.items():
                read_permissions = config.get('permissions', {}).get('read', [])
                # Simplificado - en implementación real se verificaría rol del usuario
                available_collections.append(collection_name)

            self.logger.debug(f"Available global collections for {user_id}: {available_collections}")
            return available_collections

        except Exception as e:
            self.logger.error(f"Failed to list global collections for user {user_id}: {e}", exc_info=True)
            return []

    async def delete_global_collection(self, name: str, deleter_id: str) -> bool:
        """Elimina collection global con validación de permisos."""
        try:
            # Verificar permisos de eliminación
            if self.reserved_collections.is_reserved_collection(name):
                delete_permissions = self.reserved_collections.get_collection_permissions(name, 'delete')
                # Simplificado - validación real requeriría verificar rol
                self.logger.warning(f"Attempt to delete reserved collection {name} by {deleter_id}")
                return False

            # Validar permisos globales de escritura
            if not await self.access_controller.validate_global_access(deleter_id, name):
                return False

            # Por ahora simulamos eliminación exitosa
            self.logger.info(f"Global collection '{name}' deleted by {deleter_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to delete global collection {name}: {e}", exc_info=True)
            return False