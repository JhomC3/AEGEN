# src/collections/reserved_collections.py
"""
Definición y validación de collections reservadas del sistema.

Responsabilidad única: gestionar configuración y validación de
collections globales reservadas del sistema.
"""

from typing import Dict, Any, List
from enum import Enum


class ReservedCollectionType(str, Enum):
    """Tipos de collections reservadas."""
    KNOWLEDGE_BASE = "knowledge_base"
    TEMPLATES = "templates" 
    SHARED_DOCS = "shared_docs"
    SYSTEM_CONFIG = "system_config"


class ReservedCollections:
    """Definición y validación de collections reservadas del sistema."""

    RESERVED_COLLECTIONS: Dict[str, Dict[str, Any]] = {
        'global_knowledge_base': {
            'type': ReservedCollectionType.KNOWLEDGE_BASE,
            'description': 'Base de conocimiento compartida del sistema',
            'auto_create': True,
            'permissions': {
                'read': ['ADMIN', 'SUPER_ADMIN', 'USER'],
                'write': ['ADMIN', 'SUPER_ADMIN'],
                'delete': ['SUPER_ADMIN']
            }
        },
        'global_templates': {
            'type': ReservedCollectionType.TEMPLATES,
            'description': 'Plantillas globales reutilizables',
            'auto_create': True,
            'permissions': {
                'read': ['ADMIN', 'SUPER_ADMIN', 'USER'],
                'write': ['ADMIN', 'SUPER_ADMIN'],
                'delete': ['SUPER_ADMIN']
            }
        },
        'global_shared_docs': {
            'type': ReservedCollectionType.SHARED_DOCS,
            'description': 'Documentos compartidos entre usuarios',
            'auto_create': False,
            'permissions': {
                'read': ['ADMIN', 'SUPER_ADMIN'],
                'write': ['ADMIN', 'SUPER_ADMIN'],
                'delete': ['SUPER_ADMIN']
            }
        }
    }

    RESERVED_PREFIXES = ['global_', 'system_', 'reserved_']

    @classmethod
    def is_reserved_collection(cls, collection_name: str) -> bool:
        """Verifica si nombre de collection está reservado."""
        if collection_name in cls.RESERVED_COLLECTIONS:
            return True
        
        return any(collection_name.startswith(prefix) for prefix in cls.RESERVED_PREFIXES)

    @classmethod
    def get_reserved_collection_config(cls, name: str) -> Dict[str, Any]:
        """Obtiene configuración de collection reservada."""
        return cls.RESERVED_COLLECTIONS.get(name, {})

    @classmethod
    def validate_collection_name(cls, proposed_name: str) -> bool:
        """Valida que nombre propuesto no conflicte con reservados."""
        return not cls.is_reserved_collection(proposed_name)

    @classmethod
    def list_auto_create_collections(cls) -> List[str]:
        """Lista collections que deben crearse automáticamente."""
        return [
            name for name, config in cls.RESERVED_COLLECTIONS.items()
            if config.get('auto_create', False)
        ]

    @classmethod
    def get_collection_permissions(cls, collection_name: str, operation: str) -> List[str]:
        """Obtiene roles permitidos para operación en collection."""
        config = cls.get_reserved_collection_config(collection_name)
        permissions = config.get('permissions', {})
        return permissions.get(operation, [])