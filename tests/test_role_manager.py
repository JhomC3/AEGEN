# tests/test_role_manager.py
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.core.role_manager import RoleManager
from src.core.schemas import UserRole, Permission
from src.core.vector_memory_manager import MemoryType


class TestRoleManager:
    """Tests para RoleManager con sistema de roles y permisos."""

    @pytest.fixture
    def mock_vector_manager(self):
        """Mock VectorMemoryManager para tests."""
        mock = AsyncMock()
        return mock

    @pytest.fixture
    def role_manager(self, mock_vector_manager):
        """RoleManager instance para tests."""
        return RoleManager(mock_vector_manager)

    @pytest.mark.asyncio
    async def test_default_user_role(self, role_manager, mock_vector_manager):
        """Test que usuario por defecto tiene rol USER."""
        # Simular que no hay datos de rol
        mock_vector_manager.retrieve_context.return_value = []
        
        user_role = await role_manager.get_user_role("user123")
        
        assert user_role == UserRole.USER
        mock_vector_manager.retrieve_context.assert_called_once()

    @pytest.mark.asyncio
    async def test_user_permissions(self, role_manager):
        """Test permisos por rol según ROLE_PERMISSIONS."""
        # Test USER permissions
        user_permissions = role_manager.ROLE_PERMISSIONS[UserRole.USER]
        assert Permission.READ_OWN in user_permissions
        assert Permission.WRITE_OWN in user_permissions
        assert Permission.READ_GLOBAL not in user_permissions
        
        # Test ADMIN permissions
        admin_permissions = role_manager.ROLE_PERMISSIONS[UserRole.ADMIN]
        assert Permission.READ_OWN in admin_permissions
        assert Permission.WRITE_OWN in admin_permissions
        assert Permission.READ_GLOBAL in admin_permissions
        assert Permission.WRITE_GLOBAL in admin_permissions
        assert Permission.MANAGE_USERS not in admin_permissions
        
        # Test SUPER_ADMIN permissions
        super_admin_permissions = role_manager.ROLE_PERMISSIONS[UserRole.SUPER_ADMIN]
        assert Permission.MANAGE_USERS in super_admin_permissions
        assert len(super_admin_permissions) == 5  # Todos los permisos

    @pytest.mark.asyncio
    async def test_check_permission_user_role(self, role_manager, mock_vector_manager):
        """Test verificación de permisos para rol USER."""
        # Mock usuario con rol USER
        mock_vector_manager.retrieve_context.return_value = []  # Rol por defecto
        
        # Permisos que debe tener USER
        assert await role_manager.check_permission("user123", Permission.READ_OWN) == True
        assert await role_manager.check_permission("user123", Permission.WRITE_OWN) == True
        
        # Permisos que NO debe tener USER
        assert await role_manager.check_permission("user123", Permission.READ_GLOBAL) == False
        assert await role_manager.check_permission("user123", Permission.MANAGE_USERS) == False

    @pytest.mark.asyncio
    async def test_check_permission_admin_role(self, role_manager, mock_vector_manager):
        """Test verificación de permisos para rol ADMIN."""
        # Mock usuario con rol ADMIN
        mock_vector_manager.retrieve_context.return_value = [{
            "metadata": {"user_role": "admin"}
        }]
        
        # Permisos que debe tener ADMIN
        assert await role_manager.check_permission("admin123", Permission.READ_OWN) == True
        assert await role_manager.check_permission("admin123", Permission.READ_GLOBAL) == True
        assert await role_manager.check_permission("admin123", Permission.WRITE_GLOBAL) == True
        
        # Permisos que NO debe tener ADMIN
        assert await role_manager.check_permission("admin123", Permission.MANAGE_USERS) == False

    @pytest.mark.asyncio
    async def test_grant_role_success(self, role_manager, mock_vector_manager):
        """Test otorgar rol exitosamente."""
        # Mock: granted_by tiene permisos MANAGE_USERS (SUPER_ADMIN)
        mock_vector_manager.retrieve_context.side_effect = [
            # Primera llamada: verificar permisos de granted_by
            [{"metadata": {"user_role": "super_admin"}}],
            # Segunda llamada: obtener rol del usuario (para verificar cambio)
            []
        ]
        mock_vector_manager.store_context.return_value = True
        
        result = await role_manager.grant_role("user123", UserRole.ADMIN, "super_admin_456")
        
        assert result == True
        mock_vector_manager.store_context.assert_called_once()
        
        # Verificar que se llamó con metadatos correctos
        call_args = mock_vector_manager.store_context.call_args
        assert call_args[1]["context_type"] == MemoryType.PREFERENCE
        assert "granted_by" in call_args[1]["metadata"]

    @pytest.mark.asyncio
    async def test_grant_role_insufficient_permissions(self, role_manager, mock_vector_manager):
        """Test fallar al otorgar rol sin permisos suficientes."""
        # Mock: granted_by NO tiene permisos MANAGE_USERS (es USER)
        mock_vector_manager.retrieve_context.return_value = []  # USER por defecto
        
        result = await role_manager.grant_role("user123", UserRole.ADMIN, "regular_user_456")
        
        assert result == False
        mock_vector_manager.store_context.assert_not_called()

    @pytest.mark.asyncio
    async def test_revoke_role(self, role_manager, mock_vector_manager):
        """Test revocar rol (volver a USER)."""
        # Mock: revoked_by tiene permisos MANAGE_USERS
        mock_vector_manager.retrieve_context.side_effect = [
            # Primera llamada: verificar permisos de revoked_by
            [{"metadata": {"user_role": "super_admin"}}],
            # Segunda llamada: para grant_role interno (volver a USER)
            [{"metadata": {"user_role": "super_admin"}}],
            []  # Usuario actual sin rol específico
        ]
        mock_vector_manager.store_context.return_value = True
        
        result = await role_manager.revoke_role("user123", "super_admin_456")
        
        assert result == True
        # Debe haber llamado a store_context para otorgar rol USER
        mock_vector_manager.store_context.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_user_permissions(self, role_manager, mock_vector_manager):
        """Test listar permisos de usuario."""
        # Mock usuario ADMIN
        mock_vector_manager.retrieve_context.return_value = [{
            "metadata": {"user_role": "admin"}
        }]
        
        permissions = await role_manager.list_user_permissions("admin123")
        
        expected_admin_permissions = role_manager.ROLE_PERMISSIONS[UserRole.ADMIN]
        assert permissions == expected_admin_permissions
        assert Permission.READ_GLOBAL in permissions
        assert Permission.MANAGE_USERS not in permissions

    @pytest.mark.asyncio
    async def test_error_handling(self, role_manager, mock_vector_manager):
        """Test manejo de errores en operaciones."""
        # Simular error en vector_manager
        mock_vector_manager.retrieve_context.side_effect = Exception("Database error")
        
        # En caso de error, get_user_role devuelve USER por defecto
        # Por tanto check_permission para permisos USER debe ser True
        result = await role_manager.check_permission("user123", Permission.READ_OWN)
        assert result == True  # USER tiene READ_OWN por defecto
        
        # Pero permisos elevados deben ser False
        result_global = await role_manager.check_permission("user123", Permission.READ_GLOBAL)
        assert result_global == False
        
        role = await role_manager.get_user_role("user123")
        assert role == UserRole.USER  # Fallback a USER
        
        permissions = await role_manager.list_user_permissions("user123")
        # En caso de error, list_user_permissions también devuelve set vacío
        # pero internamente llama a get_user_role que devuelve USER fallback
        expected_user_permissions = role_manager.ROLE_PERMISSIONS[UserRole.USER]
        assert permissions == expected_user_permissions  # Permisos USER por fallback