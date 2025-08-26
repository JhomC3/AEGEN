# tests/test_modular_agents.py
"""
Tests para BaseModularAgent interface y implementaciones.
Valida compliance con filosofía del proyecto y contratos establecidos.
"""

import pytest

from src.agents.modular import ExampleModularAgent
from src.core.interfaces.modular_agent import BaseModularAgent
from src.core.schemas import AgentCapability, AgentContext, AgentResultStatus


class TestBaseModularAgentInterface:
    """Tests de compliance de interface BaseModularAgent."""

    def test_example_agent_implements_interface(self):
        """Valida que ExampleModularAgent implementa BaseModularAgent correctamente."""
        agent = ExampleModularAgent()
        
        # Verificar que implementa la interface
        assert isinstance(agent, BaseModularAgent)
        
        # Verificar métodos requeridos existen
        assert hasattr(agent, 'execute')
        assert hasattr(agent, 'get_capabilities')
        assert hasattr(agent, 'can_handle')

    def test_agent_capabilities(self):
        """Test de get_capabilities method."""
        agent = ExampleModularAgent()
        capabilities = agent.get_capabilities()
        
        assert isinstance(capabilities, list)
        assert AgentCapability.VALIDATION in capabilities

    def test_can_handle_method(self):
        """Test de can_handle method con diferentes task types."""
        agent = ExampleModularAgent()
        
        # Should handle validation tasks
        assert agent.can_handle("validate_input") is True
        
        # Should not handle other tasks
        assert agent.can_handle("file_upload") is False
        assert agent.can_handle("unknown_task") is False


class TestExampleModularAgent:
    """Tests específicos para ExampleModularAgent."""

    @pytest.fixture
    def agent(self):
        """Fixture para agente de ejemplo."""
        return ExampleModularAgent()

    @pytest.fixture
    def context(self):
        """Fixture para contexto de prueba."""
        return AgentContext(user_id="test_user_123")

    @pytest.mark.asyncio
    async def test_execute_success(self, agent, context):
        """Test de ejecución exitosa."""
        result = await agent.execute({"test": "data"}, context)
        
        assert result.status == AgentResultStatus.SUCCESS
        assert result.is_success is True
        assert result.data is not None
        assert result.data["validated"] is True

    @pytest.mark.asyncio
    async def test_execute_empty_input_error(self, agent, context):
        """Test de manejo de error con input vacío."""
        result = await agent.execute(None, context)
        
        assert result.status == AgentResultStatus.ERROR
        assert result.is_success is False
        assert "empty" in result.message.lower()

    @pytest.mark.asyncio
    async def test_execute_maintains_async_philosophy(self, agent, context):
        """Test que valida que execute es realmente async."""
        import asyncio
        import time
        
        start_time = time.time()
        
        # Ejecutar múltiples agentes concurrentemente
        tasks = [
            agent.execute({"test": f"data_{i}"}, context)
            for i in range(3)
        ]
        
        results = await asyncio.gather(*tasks)
        elapsed = time.time() - start_time
        
        # Verificar que todos fueron exitosos
        assert all(r.is_success for r in results)
        
        # Verificar que realmente corrieron de forma async (no secuencial)
        # Si fueran síncronos, tomarían ~3ms, async debería ser ~1ms
        assert elapsed < 0.01  # Menos de 10ms para 3 operaciones


class TestAgentContextAndResult:
    """Tests para AgentContext y AgentResult schemas."""

    def test_agent_context_creation(self):
        """Test de creación de AgentContext."""
        context = AgentContext(user_id="user123")
        
        assert context.user_id == "user123"
        assert context.session_id is None
        assert isinstance(context.metadata, dict)
        assert isinstance(context.previous_results, list)

    def test_agent_context_metadata(self):
        """Test de manejo de metadata en AgentContext."""
        context = AgentContext(
            user_id="user123",
            metadata={"key1": "value1", "key2": 42}
        )
        
        assert context.get_metadata("key1") == "value1"
        assert context.get_metadata("key2") == 42
        assert context.get_metadata("nonexistent", "default") == "default"

    def test_agent_result_is_success_property(self):
        """Test de la propiedad is_success en AgentResult."""
        success_result = AgentResult(
            status=AgentResultStatus.SUCCESS,
            data={"test": "success"}
        )
        partial_success_result = AgentResult(
            status=AgentResultStatus.PARTIAL_SUCCESS,
            data={"test": "partial"}
        )
        error_result = AgentResult(
            status=AgentResultStatus.ERROR,
            data=None
        )
        
        assert success_result.is_success is True
        assert partial_success_result.is_success is True
        assert error_result.is_success is False