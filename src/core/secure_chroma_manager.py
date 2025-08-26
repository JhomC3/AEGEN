# src/core/secure_chroma_manager.py
import logging
from typing import Any, Dict, List, Optional

from src.core.role_manager import RoleManager
from src.core.schemas import Permission
from src.vector_db.chroma_manager import ChromaManager

logger = logging.getLogger(__name__)


class SecureChromaManager:
    """Wrapper de ChromaManager con verificación de permisos."""

    def __init__(self, chroma_manager: ChromaManager, role_manager: RoleManager):
        self.chroma_manager = chroma_manager
        self.role_manager = role_manager
        self.logger = logging.getLogger(__name__)

    async def save_user_data(
        self,
        user_id: str,
        data: Dict[str, Any],
        data_type: str = "conversation",
        requester_id: Optional[str] = None
    ) -> bool:
        """Guarda datos verificando permisos de escritura."""
        effective_user = requester_id or user_id
        
        try:
            # Verificar permisos de escritura
            if requester_id and requester_id != user_id:
                # Cross-tenant write, necesita permisos especiales
                if not await self.role_manager.check_permission(requester_id, Permission.WRITE_GLOBAL):
                    self.logger.warning(f"User {requester_id} denied cross-tenant write to {user_id}")
                    return False
            else:
                # Own data write
                if not await self.role_manager.check_permission(effective_user, Permission.WRITE_OWN):
                    self.logger.warning(f"User {effective_user} denied write access")
                    return False

            # Proceder con la operación
            return await self.chroma_manager.save_user_data(user_id, data, data_type)

        except Exception as e:
            self.logger.error(f"Failed secure save for user {user_id}: {e}", exc_info=True)
            return False

    async def query_user_data(
        self,
        user_id: str,
        query_text: str,
        data_type: Optional[str] = None,
        n_results: int = 5,
        requester_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Consulta datos verificando permisos de lectura."""
        effective_user = requester_id or user_id
        
        try:
            # Verificar permisos de lectura
            if requester_id and requester_id != user_id:
                # Cross-tenant read, necesita permisos especiales
                if not await self.role_manager.check_permission(requester_id, Permission.READ_GLOBAL):
                    self.logger.warning(f"User {requester_id} denied cross-tenant read from {user_id}")
                    return []
            else:
                # Own data read
                if not await self.role_manager.check_permission(effective_user, Permission.READ_OWN):
                    self.logger.warning(f"User {effective_user} denied read access")
                    return []

            # Proceder con la consulta
            results = await self.chroma_manager.query_user_data(
                user_id, query_text, data_type, n_results
            )
            
            # Enriquecer metadata con información de acceso
            for result in results:
                if "metadata" not in result:
                    result["metadata"] = {}
                result["metadata"]["accessed_by"] = effective_user
                result["metadata"]["owner"] = user_id
                
            return results

        except Exception as e:
            self.logger.error(f"Failed secure query for user {user_id}: {e}", exc_info=True)
            return []

    async def query_global_collection(
        self,
        requester_id: str,
        collection_name: str,
        query_text: str,
        n_results: int = 5
    ) -> List[Dict[str, Any]]:
        """Consulta collections globales con verificación de permisos."""
        try:
            # Verificar permisos globales
            if not await self.role_manager.check_permission(requester_id, Permission.READ_GLOBAL):
                self.logger.warning(f"User {requester_id} denied global collection access")
                return []

            # Para implementación futura de collections globales
            # Por ahora retornamos lista vacía ya que no están implementadas
            self.logger.info(f"Global collection {collection_name} query requested by {requester_id}")
            return []

        except Exception as e:
            self.logger.error(f"Failed global collection query: {e}", exc_info=True)
            return []

    async def can_user_access(self, requester_id: str, target_user_id: str, operation: str) -> bool:
        """Verifica si usuario puede acceder a datos de otro usuario."""
        try:
            if requester_id == target_user_id:
                # Acceso a datos propios
                if operation == "read":
                    return await self.role_manager.check_permission(requester_id, Permission.READ_OWN)
                elif operation == "write":
                    return await self.role_manager.check_permission(requester_id, Permission.WRITE_OWN)
            else:
                # Acceso cross-tenant
                if operation == "read":
                    return await self.role_manager.check_permission(requester_id, Permission.READ_GLOBAL)
                elif operation == "write":
                    return await self.role_manager.check_permission(requester_id, Permission.WRITE_GLOBAL)
                    
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to check user access: {e}", exc_info=True)
            return False