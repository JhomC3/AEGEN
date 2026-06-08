# src/core/providers/round_robin_key.py
"""
Round-Robin API Key Provider para Google Gemini.

Rotacion automatica de multiples API keys de Google AI Studio
para maximizar rate limits gratuitos.
"""

import asyncio
import os
import threading
import time


class RoundRobinKeyProvider:
    """
    Proporciona API keys de Google en rotacion round-robin.

    Lee GEMINI_API_KEY_1, GEMINI_API_KEY_2, ..., GEMINI_API_KEY_N
    desde las variables de entorno y rota en cada solicitud.

    Si una key falla por rate limit (HTTP 429), la marca como
    agotada por 60 segundos y pasa a la siguiente automaticamente.
    """

    def __init__(self) -> None:
        self._keys: list[str] = []
        self._index: int = 0
        self._cooldowns: dict[str, float] = {}
        self._lock = asyncio.Lock()
        self._sync_lock = threading.Lock()
        self._discover_keys()

    def _discover_keys(self) -> None:
        i = 1
        while True:
            key = os.environ.get(f"GEMINI_API_KEY_{i}")
            if not key:
                break
            self._keys.append(key)
            i += 1
        if not self._keys:
            single = os.environ.get("GOOGLE_API_KEY") or os.environ.get(
                "GEMINI_API_KEY"
            )
            if single:
                self._keys.append(single)

    async def get_key(self) -> str | None:
        if not self._keys:
            return None
        async with self._lock:
            now = asyncio.get_running_loop().time()
            for _ in range(len(self._keys)):
                key = self._keys[self._index]
                self._index = (self._index + 1) % len(self._keys)
                cooldown_until = self._cooldowns.get(key, 0)
                if now >= cooldown_until:
                    return key
            self._index = (self._index + 1) % len(self._keys)
            return self._keys[self._index]

    def get_key_sync(self) -> str | None:
        """Obtiene una key de forma síncrona y segura para ManagedLLM.invoke()."""
        if not self._keys:
            return None
        with self._sync_lock:
            now = time.time()
            # En contexto síncrono usamos time.time() para calcular expiraciones
            for _ in range(len(self._keys)):
                key = self._keys[self._index]
                self._index = (self._index + 1) % len(self._keys)
                cooldown_until = self._cooldowns.get(key, 0)
                if now >= cooldown_until:
                    return key
            self._index = (self._index + 1) % len(self._keys)
            return self._keys[self._index]

    async def mark_rate_limited(self, key: str) -> None:
        async with self._lock:
            self._cooldowns[key] = asyncio.get_running_loop().time() + 60

    def mark_rate_limited_sync(self, key: str) -> None:
        """Marca una key como rate-limited de forma síncrona."""
        with self._sync_lock:
            self._cooldowns[key] = time.time() + 60

    @property
    def key_count(self) -> int:
        return len(self._keys)


_round_robin_provider: RoundRobinKeyProvider | None = None


def get_round_robin_provider() -> RoundRobinKeyProvider:
    global _round_robin_provider
    if _round_robin_provider is None:
        _round_robin_provider = RoundRobinKeyProvider()
    return _round_robin_provider
