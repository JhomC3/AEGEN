import logging
from datetime import UTC, datetime

from src.core.schemas import Permission, UserRole
from src.memory.vector_memory_manager import MemoryType, VectorMemoryManager

logger = logging.getLogger(__name__)


class RoleManager:
    """Gestiona roles y permisos en el sistema."""

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
                "User %s role %s permission %s: %s",
                user_id,
                user_role,
                permission,
                has_permission,
            )

            return has_permission

        except Exception as e:
            self.logger.error("Error check permission: %s", e)
            return False

    async def get_user_role(self, user_id: str) -> UserRole:
        """Obtiene rol del usuario."""
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

                if role_value and role_value in [r.value for r in UserRole]:
                    return UserRole(role_value)

            return UserRole.USER

        except Exception as e:
            self.logger.error("Error get user role: %s", e)
            return UserRole.USER

    async def grant_role(self, user_id: str, role: UserRole, granted_by: str) -> bool:
        """Otorga rol a usuario."""
        try:
            if not await self.check_permission(granted_by, Permission.MANAGE_USERS):
                return False

            role_metadata = {
                "user_role": role.value,
                "granted_by": granted_by,
                "granted_at": datetime.now(UTC).isoformat(),
                "permissions": [p.value for p in self.ROLE_PERMISSIONS[role]],
            }

            stored_count = await self.vector_manager.store_context(
                user_id=user_id,
                content=f"User role: {role.value}",
                context_type=MemoryType.PREFERENCE,
                metadata=role_metadata,
            )
            return stored_count > 0

        except Exception as e:
            self.logger.error("Error grant role: %s", e)
            return False

    async def list_user_permissions(self, user_id: str) -> set[Permission]:
        """Lista todos los permisos del usuario."""
        try:
            user_role = await self.get_user_role(user_id)
            return self.ROLE_PERMISSIONS.get(user_role, set())
        except Exception:
            return set()
