import io
from unittest.mock import MagicMock, patch

import pytest

from src.tools.google_file_search import GoogleFileSearchTool


@pytest.fixture
def mock_genai_client():
    with patch("src.tools.google_file_search.genai.Client") as mock:
        yield mock


@pytest.mark.asyncio
async def test_upload_from_string_prefixes_chat_id(mock_genai_client):
    # Setup
    mock_client_instance = mock_genai_client.return_value
    mock_client_instance.files.upload.return_value = MagicMock(
        name="mock_file", uri="https://test.uri"
    )
    mock_client_instance.files.get.return_value = MagicMock(
        state="ACTIVE", name="mock_file"
    )

    tool = GoogleFileSearchTool()
    chat_id = "user123"
    filename = "profile.json"
    content = '{"key": "value"}'

    # Execute
    await tool.upload_from_string(content, filename, chat_id)

    # Verify
    mock_client_instance.files.upload.assert_called_once()
    args, kwargs = mock_client_instance.files.upload.call_args

    # Check display_name in config
    assert kwargs["config"]["display_name"] == f"{chat_id}/{filename}"

    # Check that it used a stream (io.BytesIO)
    assert isinstance(kwargs["file"], io.BytesIO)
    assert kwargs["file"].getvalue().decode("utf-8") == content


@pytest.mark.asyncio
async def test_get_relevant_files_filters_by_chat_id(mock_genai_client):
    # Setup
    mock_client_instance = mock_genai_client.return_value
    mock_files = [
        MagicMock(
            display_name="user123/profile.txt", state="ACTIVE", mime_type="text/plain"
        ),
        MagicMock(
            display_name="user456/other.txt", state="ACTIVE", mime_type="text/plain"
        ),
        MagicMock(
            display_name="knowledge/therapy.pdf",
            state="ACTIVE",
            mime_type="application/pdf",
        ),
    ]
    mock_client_instance.files.list.return_value = mock_files

    tool = GoogleFileSearchTool()

    # Execute with intent_type='monitoring' to trigger global_pdfs inclusion
    relevant = await tool.get_relevant_files("user123", intent_type="monitoring")

    # Verify
    display_names = [f.display_name for f in relevant]
    assert "user123/profile.txt" in display_names
    assert "knowledge/therapy.pdf" in display_names
    assert "user456/other.txt" not in display_names
