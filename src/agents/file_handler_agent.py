# src/agents/file_handler_agent.py
import asyncio
import logging
import os
from pathlib import Path
from typing import Any

from src.agents.file_readers import READER_REGISTRY
from src.agents.file_validators import FileValidator
from src.core.interfaces.modular_agent import ModularAgentBase
from src.core.schemas import AgentCapability, AgentContext, AgentResult
from src.tools.multimodal_processor import process_multimodal_file


class FileHandlerAgent(ModularAgentBase):
    """Agente modular para procesamiento seguro de archivos."""
    
    def __init__(self):
        capabilities = [
            AgentCapability.FILE_PROCESSING,
            AgentCapability.VALIDATION
        ]
        super().__init__("FileHandlerAgent", capabilities)
        self.logger = logging.getLogger(__name__)
        self.validator = FileValidator()
        
        supported_formats = list(READER_REGISTRY.keys())
        self.logger.info(f"FileHandlerAgent initialized with: {supported_formats}")

    def can_handle(self, task_type: str, input_data: Any = None) -> bool:
        """Determina si puede manejar el tipo de tarea."""
        file_tasks = {
            "file_upload", "file_parse", "document_processing", 
            "content_extraction", "file_validation"
        }
        return task_type in file_tasks

    async def _process_file_content(self, file_path: str, extension: str) -> str:
        """Procesa contenido usando el multimodal processor."""
        try:
            file_name = Path(file_path).name
            result = await process_multimodal_file.ainvoke({
                "file_path": file_path,
                "file_name": file_name
            })
            
            if "error" in result:
                raise ValueError(result["error"])
            
            content = result.get("content", "")
            return self.validator.sanitize_content(content)
        except Exception as e:
            self.logger.error(f"Failed to process {file_path}: {e}")
            raise ValueError(f"Processing failed: {str(e)}")

    async def execute(self, input_data: Any, context: AgentContext) -> AgentResult:
        """
        Ejecuta procesamiento de archivo.
        Input: {"file_path": str, "file_name": str (optional)}
        """
        try:
            self.logger.info(f"Processing file for user {context.user_id}")
            
            # Validate input
            if not isinstance(input_data, dict):
                return self._create_error_result("Invalid input: expected dict with 'file_path'")
            
            file_path = input_data.get("file_path")
            if not file_path:
                return self._create_error_result("Missing 'file_path' in input")
            
            file_name = input_data.get("file_name", Path(file_path).name)
            
            # Security validations
            extension = self.validator.validate_all(file_path)
            
            # Process content
            content = await self._process_file_content(file_path, extension)
            
            # Build result
            result_data = {
                "content": content,
                "file_name": file_name,
                "file_size": os.path.getsize(file_path),
                "extension": extension,
                "content_length": len(content)
            }
            
            self.logger.info(f"Processed {file_name}: {len(content)} characters")
            
            return self._create_success_result(
                data=result_data,
                message=f"Successfully processed {file_name}",
                next_agents=["chat_specialist"] if content else []
            )
            
        except (FileNotFoundError, PermissionError, ValueError) as e:
            error_msg = f"File processing failed: {str(e)}"
            self.logger.warning(error_msg)
            return self._create_error_result(error_msg, str(e))
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return self._create_error_result(error_msg, str(e))