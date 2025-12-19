# src/memory/redis_fallback.py
"""
Manejo de Redis como cache rápido con fallback a ChromaDB.

Responsabilidad única: gestionar operaciones de cache Redis
con estrategias de fallback y health monitoring.
"""

import json
import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


class RedisFallbackManager:
    """Manejo de Redis como cache rápido con fallback a ChromaDB."""

    def __init__(self, redis_client=None):
        # En implementación real se inyectaría cliente Redis
        self.redis_client = redis_client
        self.logger = logging.getLogger(__name__)
        self._mock_cache: dict[str, dict[str, Any]] = {}  # Mock para development

    async def get_from_redis_or_fallback(
        self, user_id: str, query: str
    ) -> list[dict[str, Any]]:
        """Obtiene datos de Redis o indica necesidad de fallback."""
        try:
            # Verificar health de Redis primero
            if not await self.redis_health_check():
                self.logger.warning("Redis unavailable, returning empty for fallback")
                return []

            cache_key = self._build_cache_key(user_id, query)

            if self.redis_client:
                # Implementación real con Redis
                cached_data = await self.redis_client.get(cache_key)
                if cached_data:
                    return json.loads(cached_data)
            else:
                # Mock implementation
                cached_data = self._mock_cache.get(cache_key)
                if cached_data and not self._is_expired(cached_data):
                    return cached_data.get("data", [])

            return []  # No data in cache, needs fallback

        except Exception as e:
            self.logger.error(
                f"Failed Redis lookup for user {user_id}: {e}", exc_info=True
            )
            return []

    async def cache_to_redis(
        self, user_id: str, key: str, data: dict[str, Any], ttl: int
    ) -> bool:
        """Almacena datos en Redis con TTL."""
        try:
            cache_key = self._build_cache_key(user_id, key)

            cache_entry = {
                "data": data,
                "cached_at": datetime.now(UTC).isoformat(),
                "ttl": ttl,
                "expires_at": datetime.now(UTC).timestamp() + ttl,
            }

            if self.redis_client:
                # Implementación real con Redis
                await self.redis_client.setex(cache_key, ttl, json.dumps(cache_entry))
            else:
                # Mock implementation
                self._mock_cache[cache_key] = cache_entry

            self.logger.debug(f"Cached data for user {user_id}, key {key}, TTL {ttl}s")
            return True

        except Exception as e:
            self.logger.error(
                f"Failed to cache data for user {user_id}: {e}", exc_info=True
            )
            return False

    async def cache_context(self, user_id: str, content: str, ttl: int) -> bool:
        """Cache contexto conversacional."""
        context_data = {"content": content, "type": "context", "user_id": user_id}

        context_key = f"context_{hash(content) % 10000}"
        return await self.cache_to_redis(user_id, context_key, context_data, ttl)

    async def invalidate_redis_cache(self, user_id: str, pattern: str) -> bool:
        """Invalida cache de Redis para patrón específico."""
        try:
            if self.redis_client:
                # Implementación real con Redis
                keys_pattern = self._build_cache_key(user_id, pattern)
                keys = await self.redis_client.keys(keys_pattern)
                if keys:
                    await self.redis_client.delete(*keys)
                    self.logger.info(
                        f"Invalidated {len(keys)} cache entries for user {user_id}"
                    )
                    return True
            else:
                # Mock implementation
                keys_to_delete = [
                    key
                    for key in self._mock_cache.keys()
                    if user_id in key and pattern in key
                ]
                for key in keys_to_delete:
                    del self._mock_cache[key]
                self.logger.info(
                    f"Invalidated {len(keys_to_delete)} mock cache entries"
                )

            return True

        except Exception as e:
            self.logger.error(
                f"Failed to invalidate cache for user {user_id}: {e}", exc_info=True
            )
            return False

    async def redis_health_check(self) -> bool:
        """Verifica salud de conexión Redis."""
        try:
            if self.redis_client:
                await self.redis_client.ping()
                return True
            else:
                # Mock siempre disponible
                return True

        except Exception as e:
            self.logger.warning(f"Redis health check failed: {e}")
            return False

    async def get_persistent_data(self, user_id: str) -> list[dict[str, Any]]:
        """Obtiene datos que necesitan persistencia a ChromaDB."""
        try:
            persistent_data = []

            if self.redis_client:
                # Implementación real - buscar datos marcados para persistencia
                pattern = self._build_cache_key(user_id, "*persistent*")
                keys = await self.redis_client.keys(pattern)

                for key in keys:
                    data = await self.redis_client.get(key)
                    if data:
                        persistent_data.append(json.loads(data))
            else:
                # Mock implementation
                for key, cache_entry in self._mock_cache.items():
                    if user_id in key and cache_entry.get("data", {}).get(
                        "persistent", False
                    ):
                        persistent_data.append(cache_entry["data"])

            return persistent_data

        except Exception as e:
            self.logger.error(
                f"Failed to get persistent data for user {user_id}: {e}", exc_info=True
            )
            return []

    async def cleanup_expired_entries(self) -> int:
        """Limpia entradas expiradas."""
        try:
            if not self.redis_client:
                # Mock cleanup
                current_time = datetime.now(UTC).timestamp()
                expired_keys = [
                    key
                    for key, entry in self._mock_cache.items()
                    if entry.get("expires_at", 0) < current_time
                ]

                for key in expired_keys:
                    del self._mock_cache[key]

                return len(expired_keys)

            # Redis auto-expiry, return 0
            return 0

        except Exception as e:
            self.logger.error(f"Failed cleanup: {e}", exc_info=True)
            return 0

    def _build_cache_key(self, user_id: str, key: str) -> str:
        """Construye clave de cache con namespace."""
        return f"magi:user:{user_id}:{key}"

    def _is_expired(self, cache_entry: dict[str, Any]) -> bool:
        """Verifica si entrada de cache ha expirado."""
        expires_at = cache_entry.get("expires_at", 0)
        return datetime.now(UTC).timestamp() > expires_at
