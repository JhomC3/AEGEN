# tests/performance/test_chroma_collections_performance.py
"""
Performance tests para ChromaDB collections per-user vs collection única.

Task #8: Validar si approach collections per-user escala correctamente.
Decision point para collections granulares si performance insufficient.
"""

import asyncio
import logging
import time
from typing import Dict, List
from unittest.mock import MagicMock

import pytest
import psutil

from src.vector_db.chroma_manager import ChromaManager


logger = logging.getLogger(__name__)


class PerformanceMetrics:
    """Recolector de métricas de performance."""
    
    def __init__(self):
        self.metrics: Dict[str, List[float]] = {
            "latency_ms": [],
            "memory_mb": [],
            "cpu_percent": []
        }
        self.start_time: float = 0
        
    def start_measurement(self):
        """Inicia medición de performance."""
        self.start_time = time.time()
        
    def record_measurement(self, operation: str = ""):
        """Registra métricas actuales."""
        elapsed_ms = (time.time() - self.start_time) * 1000
        memory_mb = psutil.virtual_memory().used / 1024 / 1024
        cpu_percent = psutil.cpu_percent()
        
        self.metrics["latency_ms"].append(elapsed_ms)
        self.metrics["memory_mb"].append(memory_mb)
        self.metrics["cpu_percent"].append(cpu_percent)
        
        logger.info(f"{operation} - Latency: {elapsed_ms:.2f}ms, Memory: {memory_mb:.1f}MB")
        
    def get_summary(self) -> Dict[str, Dict[str, float]]:
        """Retorna resumen de métricas."""
        summary = {}
        for metric, values in self.metrics.items():
            if values:
                summary[metric] = {
                    "avg": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values),
                    "count": len(values)
                }
        return summary


@pytest.fixture
async def mock_chroma_manager():
    """ChromaManager mockeado para tests de performance."""
    from unittest.mock import AsyncMock
    
    # Mock client y embedding function
    mock_client = AsyncMock()
    mock_embedding = MagicMock()
    
    # Mock collection
    mock_collection = AsyncMock()
    
    # Configurar async mock properly
    async def mock_get_collection(*args, **kwargs):
        await asyncio.sleep(0.001)  # 1ms base latency
        return mock_collection
    
    async def mock_add(*args, **kwargs):
        await asyncio.sleep(0.001)  # 1ms base latency
        
    async def mock_query(*args, **kwargs):
        await asyncio.sleep(0.001)  # 1ms base latency
        return {"results": []}
    
    mock_client.get_or_create_collection = mock_get_collection
    mock_collection.add = mock_add
    mock_collection.query = mock_query
    
    manager = ChromaManager(mock_client, mock_embedding)
    return manager, mock_client, mock_collection


class TestSingleUserPerformance:
    """Tests baseline performance para un usuario."""
    
    async def test_single_user_save_operations(self, mock_chroma_manager):
        """Test: Performance de save operations para un usuario."""
        manager, mock_client, mock_collection = mock_chroma_manager
        metrics = PerformanceMetrics()
        
        test_data = {
            "content": "Test message content for performance testing",
            "message_id": "test_msg",
            "timestamp": "2025-08-30T10:00:00Z"
        }
        
        # Baseline: 100 save operations
        for i in range(100):
            metrics.start_measurement()
            await manager.save_user_data("user_1", {**test_data, "message_id": f"msg_{i}"})
            metrics.record_measurement(f"Save operation {i}")
            
        summary = metrics.get_summary()
        
        # Assertions: Latency debe ser < 50ms promedio
        avg_latency = summary["latency_ms"]["avg"]
        assert avg_latency < 50, f"Average latency {avg_latency:.2f}ms too high"
        
        # Verify se usó la collection correcta
        mock_client.get_or_create_collection.assert_called()
        assert mock_collection.add.call_count == 100


class TestMultiUserConcurrency:
    """Tests performance con múltiples usuarios concurrentes."""
    
    async def test_concurrent_users_10(self, mock_chroma_manager):
        """Test: 10 usuarios concurrentes."""
        manager, mock_client, mock_collection = mock_chroma_manager
        metrics = PerformanceMetrics()
        
        async def user_workload(user_id: str):
            """Workload para un usuario: 10 save operations."""
            for i in range(10):
                test_data = {
                    "content": f"Message from user {user_id}",
                    "message_id": f"{user_id}_msg_{i}"
                }
                await manager.save_user_data(user_id, test_data)
        
        # Test: 10 usuarios concurrentes
        metrics.start_measurement()
        
        tasks = [user_workload(f"user_{i}") for i in range(10)]
        await asyncio.gather(*tasks)
        
        metrics.record_measurement("10 concurrent users")
        summary = metrics.get_summary()
        
        # Assertions: Total time debe ser razonable
        total_latency = summary["latency_ms"]["avg"]
        assert total_latency < 1000, f"Concurrent execution too slow: {total_latency:.2f}ms"
        
        # Verify: Se crearon 10 collections diferentes
        expected_calls = 10  # Una por usuario
        actual_calls = mock_client.get_or_create_collection.call_count
        assert actual_calls >= expected_calls, f"Expected {expected_calls} collections, got {actual_calls}"
        
    async def test_concurrent_users_100(self, mock_chroma_manager):
        """Test: 100 usuarios concurrentes - stress test."""
        manager, mock_client, mock_collection = mock_chroma_manager
        metrics = PerformanceMetrics()
        
        async def lightweight_user_workload(user_id: str):
            """Workload ligero: 1 save operation por usuario."""
            test_data = {
                "content": f"Test from user {user_id}",
                "message_id": f"{user_id}_msg"
            }
            await manager.save_user_data(user_id, test_data)
        
        # Test: 100 usuarios concurrentes
        metrics.start_measurement()
        
        tasks = [lightweight_user_workload(f"user_{i}") for i in range(100)]
        await asyncio.gather(*tasks)
        
        metrics.record_measurement("100 concurrent users")
        summary = metrics.get_summary()
        
        # Assertions: Debe completar en tiempo razonable
        total_latency = summary["latency_ms"]["avg"]
        assert total_latency < 5000, f"100 users execution too slow: {total_latency:.2f}ms"
        
        logger.info(f"100 concurrent users performance: {summary}")


class TestCollectionOverhead:
    """Tests overhead de múltiples collections."""
    
    async def test_collection_creation_overhead(self, mock_chroma_manager):
        """Test: Overhead de crear múltiples collections."""
        manager, mock_client, mock_collection = mock_chroma_manager
        metrics = PerformanceMetrics()
        
        # Test: Crear 1000 collections vacías
        metrics.start_measurement()
        
        for i in range(1000):
            await manager._get_user_collection(f"user_{i}")
            
        metrics.record_measurement("1000 collections creation")
        summary = metrics.get_summary()
        
        # Assertions: Creation time debe ser razonable
        avg_latency = summary["latency_ms"]["avg"]
        assert avg_latency < 10000, f"Collection creation too slow: {avg_latency:.2f}ms"
        
        # Verify: Se intentaron crear 1000 collections
        assert mock_client.get_or_create_collection.call_count == 1000


class TestPerformanceComparison:
    """Tests comparativos de performance."""
    
    async def test_memory_usage_scaling(self, mock_chroma_manager):
        """Test: Usar memoria con scaling de usuarios."""
        manager, mock_client, mock_collection = mock_chroma_manager
        
        # Medir memoria inicial
        initial_memory = psutil.virtual_memory().used / 1024 / 1024
        
        # Simular 50 usuarios con datos
        for user_id in range(50):
            for msg_id in range(5):  # 5 mensajes por usuario
                test_data = {
                    "content": f"Message {msg_id} from user {user_id}" * 10,  # Contenido más largo
                    "message_id": f"user_{user_id}_msg_{msg_id}"
                }
                await manager.save_user_data(f"user_{user_id}", test_data)
        
        # Medir memoria final
        final_memory = psutil.virtual_memory().used / 1024 / 1024
        memory_increase = final_memory - initial_memory
        
        logger.info(f"Memory increase for 50 users: {memory_increase:.1f}MB")
        
        # Assertion: Memory increase debe ser razonable (< 100MB para test mockeado)
        assert memory_increase < 100, f"Memory usage too high: {memory_increase:.1f}MB"


@pytest.mark.performance
class TestPerformanceDecisionPoint:
    """Tests para decision point: ¿Collections per-user escalan?"""
    
    async def test_scalability_decision_metrics(self, mock_chroma_manager):
        """
        Test principal: Métricas para tomar decisión arquitectónica.
        
        Decision criteria:
        - Latency promedio < 100ms para operaciones básicas
        - Memory usage escalable linealmente 
        - Concurrent users handling > 50 simultáneos
        """
        manager, mock_client, mock_collection = mock_chroma_manager
        
        # Test 1: Latency baseline
        start_time = time.time()
        await manager.save_user_data("test_user", {"content": "test", "message_id": "test"})
        baseline_latency = (time.time() - start_time) * 1000
        
        # Test 2: Concurrent users capacity
        async def user_task(user_id: str):
            await manager.save_user_data(f"user_{user_id}", {
                "content": f"Message from user {user_id}",
                "message_id": f"{user_id}_msg"
            })
        
        start_time = time.time()
        tasks = [user_task(str(i)) for i in range(50)]
        await asyncio.gather(*tasks)
        concurrent_latency = (time.time() - start_time) * 1000
        
        # Decision metrics
        decision_metrics = {
            "baseline_latency_ms": baseline_latency,
            "concurrent_50_users_ms": concurrent_latency,
            "collections_created": mock_client.get_or_create_collection.call_count,
            "scale_factor": concurrent_latency / baseline_latency if baseline_latency > 0 else float('inf')
        }
        
        logger.info(f"DECISION METRICS: {decision_metrics}")
        
        # Decision criteria assertions
        assert baseline_latency < 100, f"Baseline latency too high: {baseline_latency:.2f}ms"
        assert concurrent_latency < 2000, f"Concurrent latency too high: {concurrent_latency:.2f}ms"
        assert decision_metrics["scale_factor"] < 50, f"Poor scalability factor: {decision_metrics['scale_factor']:.2f}"
        
        # Store metrics for reporting
        return decision_metrics


# Configuración pytest para ejecutar solo tests performance
def pytest_configure(config):
    """Configurar pytest markers."""
    config.addinivalue_line(
        "markers", "performance: marks tests as performance tests (deselect with '-m \"not performance\"')"
    )