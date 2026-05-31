"""Tests del RoundRobinKeyProvider."""

import asyncio
import os

import pytest

from src.core.providers.round_robin_key import RoundRobinKeyProvider


def test_discovers_single_key() -> None:
    """Con una sola key, el provider la retorna."""
    provider = RoundRobinKeyProvider()
    if provider._keys:
        assert provider.key_count >= 1


def test_empty_when_no_keys() -> None:
    """Sin keys configuradas, retorna lista vacia."""
    original = {}
    for key in os.environ:
        if key.startswith("GEMINI_API_KEY") or key == "GOOGLE_API_KEY":
            original[key] = os.environ.pop(key)

    try:
        provider = RoundRobinKeyProvider()
        assert provider.key_count == 0
    finally:
        for k, v in original.items():
            os.environ[k] = v


@pytest.mark.asyncio
async def test_get_key_returns_valid_key() -> None:
    """get_key retorna una key valida cuando hay keys configuradas."""
    provider = RoundRobinKeyProvider()
    if provider.key_count == 0:
        pytest.skip("No API keys configured")

    key = await provider.get_key()
    assert key is not None
    assert key in provider._keys


@pytest.mark.asyncio
async def test_mark_rate_limited_applies_cooldown() -> None:
    """mark_rate_limited pone la key en cooldown."""
    provider = RoundRobinKeyProvider()
    if provider.key_count == 0:
        pytest.skip("No API keys configured")

    key = provider._keys[0]
    await provider.mark_rate_limited(key)

    # La key debe estar en cooldowns
    assert key in provider._cooldowns
    assert provider._cooldowns[key] > asyncio.get_running_loop().time()
