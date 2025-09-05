# src/collections/collections_factory.py
"""
Factory para componentes de collections globales.

Responsabilidad única: crear e inyectar dependencias entre
componentes de gestión de collections globales.
"""

import logging
from typing import Optional

from src.collections.reserved_collections import ReservedCollections
from src.collections.global_manager import GlobalCollectionManager
from src.collections.contribution_handler import ContributionHandler
from src.core.security.access_controller import AccessController
from src.vector_db.chroma_manager import ChromaManager

logger = logging.getLogger(__name__)


class CollectionsFactory:
    """Factory para componentes de collections globales."""

    def __init__(self, chroma_manager: ChromaManager, access_controller: AccessController):
        self.chroma_manager = chroma_manager
        self.access_controller = access_controller
        self.logger = logging.getLogger(__name__)
        
        # Cache de componentes
        self._reserved_collections: Optional[ReservedCollections] = None
        self._global_manager: Optional[GlobalCollectionManager] = None
        self._contribution_handler: Optional[ContributionHandler] = None

    def get_reserved_collections(self) -> ReservedCollections:
        """Crea o retorna ReservedCollections singleton."""
        if self._reserved_collections is None:
            self._reserved_collections = ReservedCollections()
            self.logger.debug("Created ReservedCollections instance")
        return self._reserved_collections

    def get_global_manager(self) -> GlobalCollectionManager:
        """Crea o retorna GlobalCollectionManager con dependencias."""
        if self._global_manager is None:
            self._global_manager = GlobalCollectionManager(
                self.chroma_manager,
                self.access_controller
            )
            self.logger.debug("Created GlobalCollectionManager instance")
        return self._global_manager

    def get_contribution_handler(self) -> ContributionHandler:
        """Crea o retorna ContributionHandler con dependencias."""
        if self._contribution_handler is None:
            global_manager = self.get_global_manager()
            self._contribution_handler = ContributionHandler(
                global_manager,
                self.access_controller
            )
            self.logger.debug("Created ContributionHandler instance")
        return self._contribution_handler

    def create_collections_components(self) -> dict:
        """Crea todos los componentes de collections."""
        return {
            'reserved_collections': self.get_reserved_collections(),
            'global_manager': self.get_global_manager(),
            'contribution_handler': self.get_contribution_handler()
        }