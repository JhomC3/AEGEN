# src/collections/contribution_handler.py
"""
Manejo de contribuciones a collections globales.

Responsabilidad única: gestionar flujo de contribuciones, aprobaciones
y rechazos para collections globales del sistema.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List
from enum import Enum

from src.collections.global_manager import GlobalCollectionManager
from src.core.security.access_controller import AccessController

logger = logging.getLogger(__name__)


class ContributionStatus(str, Enum):
    """Estados de contribuciones."""
    PENDING = "pending"
    APPROVED = "approved" 
    REJECTED = "rejected"


class ContributionHandler:
    """Manejo de contribuciones a collections globales."""

    def __init__(self, global_manager: GlobalCollectionManager, access_controller: AccessController):
        self.global_manager = global_manager
        self.access_controller = access_controller
        self.logger = logging.getLogger(__name__)
        # En implementación real, esto sería persistido en BD
        self._contributions_cache: Dict[str, Dict[str, Any]] = {}

    async def contribute_to_global(self, user_id: str, collection_name: str, content: Dict[str, Any]) -> bool:
        """Envía contribución a collection global para aprobación."""
        try:
            # Validar permisos básicos de contribución
            if not await self.access_controller.validate_global_access(user_id, collection_name):
                self.logger.warning(f"User {user_id} denied contribution access to {collection_name}")
                return False

            # Crear ID único para contribución
            contribution_id = f"{collection_name}_{user_id}_{datetime.now(timezone.utc).timestamp()}"
            
            # Crear registro de contribución
            contribution_record = {
                'id': contribution_id,
                'collection_name': collection_name,
                'contributor_id': user_id,
                'content': content,
                'status': ContributionStatus.PENDING,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'metadata': {
                    'content_type': content.get('type', 'unknown'),
                    'content_size': len(str(content)),
                    'requires_review': True
                }
            }
            
            # Almacenar en cache temporal
            self._contributions_cache[contribution_id] = contribution_record
            
            self.logger.info(f"Contribution {contribution_id} submitted by {user_id} to {collection_name}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to submit contribution: {e}", exc_info=True)
            return False

    async def approve_contribution(self, approver_id: str, contribution_id: str) -> bool:
        """Aprueba contribución pendiente."""
        try:
            # Verificar que contribución existe
            contribution = self._contributions_cache.get(contribution_id)
            if not contribution:
                self.logger.warning(f"Contribution {contribution_id} not found")
                return False

            # Validar permisos de aprobación
            collection_name = contribution['collection_name']
            if not await self.access_controller.validate_global_access(approver_id, collection_name):
                self.logger.warning(f"User {approver_id} denied approval access to {collection_name}")
                return False

            # Verificar estado actual
            if contribution['status'] != ContributionStatus.PENDING:
                self.logger.warning(f"Contribution {contribution_id} already processed: {contribution['status']}")
                return False

            # Actualizar estado
            contribution.update({
                'status': ContributionStatus.APPROVED,
                'approved_by': approver_id,
                'approved_at': datetime.now(timezone.utc).isoformat()
            })

            # Aquí se integraría con sistema real para añadir contenido a collection
            self.logger.info(f"Contribution {contribution_id} approved by {approver_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to approve contribution {contribution_id}: {e}", exc_info=True)
            return False

    async def reject_contribution(self, approver_id: str, contribution_id: str, reason: str) -> bool:
        """Rechaza contribución con razón."""
        try:
            # Verificar que contribución existe
            contribution = self._contributions_cache.get(contribution_id)
            if not contribution:
                self.logger.warning(f"Contribution {contribution_id} not found")
                return False

            # Validar permisos de rechazo
            collection_name = contribution['collection_name']
            if not await self.access_controller.validate_global_access(approver_id, collection_name):
                self.logger.warning(f"User {approver_id} denied rejection access to {collection_name}")
                return False

            # Actualizar estado
            contribution.update({
                'status': ContributionStatus.REJECTED,
                'rejected_by': approver_id,
                'rejected_at': datetime.now(timezone.utc).isoformat(),
                'rejection_reason': reason
            })

            self.logger.info(f"Contribution {contribution_id} rejected by {approver_id}: {reason}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to reject contribution {contribution_id}: {e}", exc_info=True)
            return False

    async def list_pending_contributions(self, collection_name: str) -> List[Dict[str, Any]]:
        """Lista contribuciones pendientes para collection."""
        try:
            pending_contributions = [
                contrib for contrib in self._contributions_cache.values()
                if contrib['collection_name'] == collection_name 
                and contrib['status'] == ContributionStatus.PENDING
            ]
            
            self.logger.debug(f"Found {len(pending_contributions)} pending contributions for {collection_name}")
            return pending_contributions

        except Exception as e:
            self.logger.error(f"Failed to list pending contributions: {e}", exc_info=True)
            return []