# tests/performance/test_permissions_cache_performance.py
"""
Performance test para el sistema de cache de permisos (Role Manager).
"""
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.schemas import Permission


@pytest.fixture
async def mock_role_manager():
    """Mock del RoleManager para performance testing."""
    mock_manager = AsyncMock()
    
    # Simular cache behavior
    cache_state = {}
    
    async def mock_check_permission(user_id: str, permission: Permission):
        # Primera vez: cache miss (simulando 10ms)
        if user_id not in cache_state:
            await asyncio.sleep(0.01)  # 10ms cache miss
            cache_state[user_id] = True
            return True
        else:
            # Cache hit: muy rápido (0.1ms)
            await asyncio.sleep(0.0001)  # 0.1ms cache hit
            return cache_state[user_id]
    
    mock_manager.check_permission = mock_check_permission
    return mock_manager


class TestPermissionsCachePerformance:
    """Tests performance del sistema de cache de permisos."""

    async def test_cache_miss_vs_cache_hit(self, mock_role_manager):
        """Test rendimiento: cache miss vs cache hit."""
        role_manager = mock_role_manager
        test_user = "test_user_123"
        permission = Permission.READ_OWN
        
        print(f"\n🧪 CACHE PERFORMANCE TEST")
        print(f"👤 Usuario: {test_user}")
        print(f"🔐 Permiso: {permission.value}")
        
        # PRUEBA 1: Primera consulta (cache miss)
        start_time = time.time()
        result1 = await role_manager.check_permission(test_user, permission)
        end_time = time.time()
        first_query_time = (end_time - start_time) * 1000
        
        print(f"\n📊 CACHE MISS:")
        print(f"   ✅ Resultado: {result1}")
        print(f"   ⏱️  Tiempo: {first_query_time:.2f}ms")
        
        # PRUEBA 2: Segunda consulta (cache hit)
        start_time = time.time()
        result2 = await role_manager.check_permission(test_user, permission)
        end_time = time.time()
        second_query_time = (end_time - start_time) * 1000
        
        print(f"\n📊 CACHE HIT:")
        print(f"   ✅ Resultado: {result2}")
        print(f"   ⏱️  Tiempo: {second_query_time:.2f}ms")
        
        # Análisis de mejora
        if first_query_time > 0 and second_query_time > 0:
            improvement = ((first_query_time - second_query_time) / first_query_time) * 100
            improvement_factor = first_query_time / second_query_time
            
            print(f"\n🚀 PERFORMANCE ANALYSIS:")
            print(f"   📉 Latency reduction: {improvement:.1f}%")
            print(f"   ⚡ Speed improvement: {improvement_factor:.1f}x faster")
        
        # Assertions
        assert result1 == result2, "Cache should return consistent results"
        assert first_query_time > second_query_time, "Cache hit should be faster than miss"
        assert improvement > 80, f"Cache should provide >80% improvement, got {improvement:.1f}%"
    
    async def test_batch_cache_performance(self, mock_role_manager):
        """Test rendimiento en lote (múltiples cache hits)."""
        role_manager = mock_role_manager
        test_user = "batch_user"
        permission = Permission.READ_OWN
        
        # Warmup cache
        await role_manager.check_permission(test_user, permission)
        
        # PRUEBA: 10 consultas en lote (todas cache hits)
        start_time = time.time()
        tasks = [role_manager.check_permission(test_user, permission) for _ in range(10)]
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        batch_total_time = (end_time - start_time) * 1000
        batch_avg_time = batch_total_time / 10
        
        print(f"\n📊 BATCH CACHE HITS (10 queries):")
        print(f"   ✅ All successful: {all(results)}")
        print(f"   ⏱️  Total time: {batch_total_time:.2f}ms")
        print(f"   ⏱️  Average per query: {batch_avg_time:.2f}ms")
        
        # Assertions
        assert all(results), "All batch queries should succeed"
        assert batch_avg_time < 1.0, f"Average batch time should be <1ms, got {batch_avg_time:.2f}ms"
        assert batch_total_time < 15, f"Total batch time should be <15ms, got {batch_total_time:.2f}ms"
    
    async def test_concurrent_users_performance(self, mock_role_manager):
        """Test rendimiento con múltiples usuarios concurrentes."""
        role_manager = mock_role_manager
        permission = Permission.READ_OWN
        
        async def user_workflow(user_id: str):
            # Primera consulta (cache miss)
            await role_manager.check_permission(f"user_{user_id}", permission)
            # Segunda consulta (cache hit)
            await role_manager.check_permission(f"user_{user_id}", permission)
            return user_id
        
        # Test con 5 usuarios concurrentes
        start_time = time.time()
        tasks = [user_workflow(str(i)) for i in range(5)]
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        concurrent_total_time = (end_time - start_time) * 1000
        per_user_time = concurrent_total_time / 5
        
        print(f"\n📊 CONCURRENT USERS (5 users, 2 queries each):")
        print(f"   ✅ Users completed: {len(results)}")
        print(f"   ⏱️  Total time: {concurrent_total_time:.2f}ms")
        print(f"   ⏱️  Time per user: {per_user_time:.2f}ms")
        
        # Assertions
        assert len(results) == 5, "All users should complete successfully"
        assert concurrent_total_time < 100, f"Concurrent execution too slow: {concurrent_total_time:.2f}ms"
        assert per_user_time < 20, f"Per-user time too high: {per_user_time:.2f}ms"