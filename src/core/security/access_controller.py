# src/core/security/access_controller.py
"""
Simple AccessController para validación de permisos de collections globales.

Implementación básica para MVP que puede ser extendida más tarde con
funcionalidad más robusta de autorización.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class AccessController:
    """
    Controlador de acceso simple para collections globales.

    Responsabilidad única: validar permisos básicos de acceso a
    collections globales basado en user_id y collection_name.

    Para MVP: implementación permisiva que logea accesos.
    TODO: Integrar con sistema de roles más robusto en futuras iteraciones.
    """

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)
        self.logger.info("Simple AccessController initialized (MVP mode)")

    async def validate_global_access(
        self, user_id: str, collection_name: str, operation: str = "read"
    ) -> bool:
        """
        Valida si usuario tiene acceso a collection global.

        Args:
            user_id: ID del usuario solicitante
            collection_name: Nombre de la collection global
            operation: Tipo de operación (read, write, delete)

        Returns:
            bool: True si acceso permitido, False si denegado
        """
        # MVP: Permitir todos los accesos pero logear para auditoria
        self.logger.info(
            f"Access request: user={user_id}, collection={collection_name}, "
            f"operation={operation} -> GRANTED (MVP mode)"
        )

        # TODO: Implementar validación real basada en roles y permisos
        # Para MVP, siempre permitimos acceso
        return True

    async def log_access_attempt(
        self,
        user_id: str,
        collection_name: str,
        operation: str,
        success: bool,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Registra intento de acceso para auditoria.

        Args:
            user_id: ID del usuario
            collection_name: Collection accedida
            operation: Operación realizada
            success: Si el acceso fue exitoso
            metadata: Metadata adicional del acceso
        """
        status = "SUCCESS" if success else "FAILED"
        meta_str = f", metadata={metadata}" if metadata else ""

        self.logger.info(
            f"Access audit: user={user_id}, collection={collection_name}, "
            f"operation={operation}, status={status}{meta_str}"
        )
