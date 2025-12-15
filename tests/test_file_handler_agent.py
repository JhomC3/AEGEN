# tests/test_file_handler_agent.py
import os
import tempfile

import pytest

from src.agents.file_handler_agent import FileHandlerAgent
from src.core.schemas import AgentCapability, AgentContext


class TestFileHandlerAgent:
    """Tests para FileHandlerAgent."""

    @pytest.fixture
    def agent(self):
        """FileHandlerAgent instance."""
        return FileHandlerAgent()

    @pytest.fixture
    def context(self):
        """AgentContext para tests."""
        return AgentContext(user_id="test_user", request_id="test_req")

    @pytest.fixture
    def temp_txt_file(self):
        """Crea archivo temporal de texto."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Test content\nLine 2")
            temp_path = f.name
        yield temp_path
        os.unlink(temp_path)

    @pytest.fixture
    def empty_txt_file(self):
        """Crea archivo temporal vacío."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("")
            temp_path = f.name
        yield temp_path
        os.unlink(temp_path)

    def test_agent_capabilities(self, agent):
        """Test que agente tiene capacidades correctas."""
        capabilities = agent.get_capabilities()
        assert AgentCapability.FILE_PROCESSING in capabilities
        assert AgentCapability.VALIDATION in capabilities

    def test_can_handle_file_tasks(self, agent):
        """Test que puede manejar tareas de archivos."""
        assert agent.can_handle("file_upload") is True
        assert agent.can_handle("file_parse") is True
        assert agent.can_handle("document_processing") is True
        assert agent.can_handle("content_extraction") is True
        assert agent.can_handle("file_validation") is True
        assert agent.can_handle("other_task") is False

    @pytest.mark.asyncio
    async def test_process_valid_txt_file(self, agent, context, temp_txt_file):
        """Test procesamiento exitoso de archivo válido."""
        input_data = {
            "file_path": temp_txt_file,
            "file_name": "test.txt"
        }

        result = await agent.execute(input_data, context)

        assert result.status == "success"
        assert "Test content" in result.data["content"]
        assert result.data["file_name"] == "test.txt"
        assert result.data["extension"] == ".txt"
        assert result.data["content_length"] > 0
        assert "NLPParserAgent" in result.next_suggested_agents

    @pytest.mark.asyncio
    async def test_missing_file_path(self, agent, context):
        """Test error con file_path faltante."""
        input_data = {"file_name": "test.txt"}

        result = await agent.execute(input_data, context)

        assert result.status == "error"
        assert "Missing 'file_path'" in result.message

    @pytest.mark.asyncio
    async def test_invalid_input_format(self, agent, context):
        """Test error con formato de input inválido."""
        input_data = "invalid input"

        result = await agent.execute(input_data, context)

        assert result.status == "error"
        assert "Invalid input" in result.message

    @pytest.mark.asyncio
    async def test_nonexistent_file(self, agent, context):
        """Test error con archivo inexistente."""
        input_data = {
            "file_path": "/nonexistent/file.txt"
        }

        result = await agent.execute(input_data, context)

        assert result.status == "error"
        assert "File does not exist" in result.message

    @pytest.mark.asyncio
    async def test_empty_file_error(self, agent, context, empty_txt_file):
        """Test error con archivo vacío."""
        input_data = {
            "file_path": empty_txt_file
        }

        result = await agent.execute(input_data, context)

        assert result.status == "error"
        assert "empty" in result.message.lower()

    @pytest.mark.asyncio
    async def test_unsupported_extension(self, agent, context):
        """Test error con extensión no soportada."""
        with tempfile.NamedTemporaryFile(suffix='.exe', delete=False) as f:
            f.write(b"binary content")
            temp_path = f.name

        try:
            input_data = {"file_path": temp_path}
            result = await agent.execute(input_data, context)

            assert result.status == "error"
            assert "not allowed" in result.message
        finally:
            os.unlink(temp_path)
