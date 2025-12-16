# src/core/role_manager.py
import logging
from datetime import UTC, datetime

from src.core.schemas import Permission, UserRole
from src.core.vector_memory_manager import MemoryType, VectorMemoryManager

logger = logging.getLogger(__name__)


class RoleManager:
    """Gestiona roles y permisos de usuarios en el sistema multi-tenant."""

    ROLE_PERMISSIONS: dict[UserRole, set[Permission]] = {
        UserRole.USER: {Permission.READ_OWN, Permission.WRITE_OWN},
        UserRole.ADMIN: {
            Permission.READ_OWN,
            Permission.WRITE_OWN,
            Permission.READ_GLOBAL,
            Permission.WRITE_GLOBAL,
        },
        UserRole.SUPER_ADMIN: {
            Permission.READ_OWN,
            Permission.WRITE_OWN,
            Permission.READ_GLOBAL,
            Permission.WRITE_GLOBAL,
            Permission.MANAGE_USERS,
        },
    }

    def __init__(self, vector_memory_manager: VectorMemoryManager):
        self.vector_manager = vector_memory_manager
        self.logger = logging.getLogger(__name__)

    async def check_permission(self, user_id: str, permission: Permission) -> bool:
        """Verifica si usuario tiene permiso específico."""
        try:
            user_role = await self.get_user_role(user_id)
            role_permissions = self.ROLE_PERMISSIONS.get(user_role, set())

            has_permission = permission in role_permissions
            self.logger.debug(
                f"User {user_id} role {user_role} has permission {permission}: {has_permission}"
            )

            return has_permission

        except Exception as e:
            self.logger.error(
                f"Failed to check permission for user {user_id}: {e}", exc_info=True
            )
            return False

    async def get_user_role(self, user_id: str) -> UserRole:
        """Obtiene rol del usuario, USER por defecto."""
        try:
            role_results = await self.vector_manager.retrieve_context(
                user_id=user_id,
                query=f"user role permissions for {user_id}",
                context_type=MemoryType.PREFERENCE,
                limit=1,
            )

            if role_results:
                role_data = role_results[0].get("metadata", {})
                role_value = role_data.get("user_role")

                if role_value and role_value in [role.value for role in UserRole]:
                    return UserRole(role_value)

            self.logger.debug(f"No role found for user {user_id}, defaulting to USER")
            return UserRole.USER

        except Exception as e:
            self.logger.error(
                f"Failed to get user role for {user_id}: {e}", exc_info=True
            )
            return UserRole.USER

    async def grant_role(self, user_id: str, role: UserRole, granted_by: str) -> bool:
        """Otorga rol a usuario con auditoría."""
        try:
            # Verificar que quien otorga tenga permisos
            if not await self.check_permission(granted_by, Permission.MANAGE_USERS):
                self.logger.warning(
                    f"User {granted_by} attempted to grant role without permission"
                )
                return False

            role_metadata = {
                "user_role": role.value,
                "granted_by": granted_by,
                "granted_at": datetime.now(UTC).isoformat(),
                "permissions": [perm.value for perm in self.ROLE_PERMISSIONS[role]],
            }

            content = f"User role: {role.value}, granted by: {granted_by}"

            success = await self.vector_manager.store_context(
                user_id=user_id,
                content=content,
                context_type=MemoryType.PREFERENCE,
                metadata=role_metadata,
            )

            if success:
                self.logger.info(
                    f"Role {role.value} granted to user {user_id} by {granted_by}"
                )

            return success

        except Exception as e:
            self.logger.error(
                f"Failed to grant role to user {user_id}: {e}", exc_info=True
            )
            return False

    async def revoke_role(self, user_id: str, revoked_by: str) -> bool:
        """Revoca rol de usuario (vuelve a USER por defecto)."""
        try:
            if not await self.check_permission(revoked_by, Permission.MANAGE_USERS):
                self.logger.warning(
                    f"User {revoked_by} attempted to revoke role without permission"
                )
                return False

            return await self.grant_role(user_id, UserRole.USER, revoked_by)

        except Exception as e:
            self.logger.error(
                f"Failed to revoke role for user {user_id}: {e}", exc_info=True
            )
            return False

    async def list_user_permissions(self, user_id: str) -> set[Permission]:
        """Lista todos los permisos del usuario según su rol."""
        try:
            user_role = await self.get_user_role(user_id)
            return self.ROLE_PERMISSIONS.get(user_role, set())

        except Exception as e:
            self.logger.error(
                f"Failed to list permissions for user {user_id}: {e}", exc_info=True
            )
            return set()
