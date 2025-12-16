# src/core/entitlements/entitlement_cache.py
"""
Cache simple de roles de usuario para optimización de rendimiento.
"""

import logging
from datetime import datetime, timedelta
from typing import Any

from src.core.schemas import UserRole

logger = logging.getLogger(__name__)


class EntitlementCache:
    """Cache simple de roles de usuario con TTL de 24 horas."""

    def __init__(self, ttl_hours: int = 24):
        self.cache: dict[str, tuple[UserRole, datetime]] = {}
        self.ttl = timedelta(hours=ttl_hours)
        self.logger = logging.getLogger(__name__)
        self.stats = {"hits": 0, "misses": 0}

    def get_user_role(self, user_id: str) -> UserRole | None:
        """
        Obtiene rol del usuario desde cache.

        Args:
            user_id: ID del usuario

        Returns:
            UserRole o None si no está en cache o expiró
        """
        if user_id not in self.cache:
            self.stats["misses"] += 1
            return None

        role, cached_at = self.cache[user_id]

        # Verificar TTL
        if datetime.now() - cached_at > self.ttl:
            del self.cache[user_id]
            self.logger.debug(f"Cache expired for user {user_id}")
            self.stats["misses"] += 1
            return None

        self.stats["hits"] += 1
        self.logger.debug(f"Cache hit for user {user_id}: {role.value}")
        return role

    def set_user_role(self, user_id: str, role: UserRole) -> None:
        """
        Guarda rol del usuario en cache.

        Args:
            user_id: ID del usuario
            role: Rol del usuario
        """
        self.cache[user_id] = (role, datetime.now())
        self.logger.debug(f"Cached role {role.value} for user {user_id}")

    def invalidate_user(self, user_id: str) -> None:
        """Invalida cache para usuario específico."""
        self.cache.pop(user_id, None)
        self.logger.debug(f"Invalidated cache for user {user_id}")

    def clear_all(self) -> None:
        """Limpia todo el cache."""
        self.cache.clear()
        self.stats = {"hits": 0, "misses": 0}
        self.logger.info("Permission cache cleared")

    def get_stats(self) -> dict[str, Any]:
        """Obtiene estadísticas del cache."""
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_ratio = (
            (self.stats["hits"] / total_requests * 100) if total_requests > 0 else 0
        )

        return {
            "cached_users": len(self.cache),
            "cache_hits": self.stats["hits"],
            "cache_misses": self.stats["misses"],
            "hit_ratio": f"{hit_ratio:.1f}%",
        }


# Instancia global del cache
entitlement_cache = EntitlementCache()
