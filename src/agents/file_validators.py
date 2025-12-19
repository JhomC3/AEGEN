# src/agents/file_validators.py
import mimetypes
import os
from pathlib import Path

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
MAX_CONTENT_SIZE = 1024 * 1024  # 1MB

ALLOWED_EXTENSIONS = {".txt", ".md", ".pdf", ".docx", ".pptx", ".xlsx", ".csv"}

ALLOWED_MIME_TYPES = {
    "text/plain",
    "text/markdown",
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/csv",
}


class FileValidator:
    """Validador de seguridad para archivos."""

    @staticmethod
    def validate_file_path(file_path: str) -> None:
        """Valida existencia y acceso del archivo."""
        if not file_path:
            raise ValueError("File path cannot be empty")

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File does not exist: {file_path}")

        if not path.is_file():
            raise ValueError(f"Path is not a file: {file_path}")

        if not os.access(file_path, os.R_OK):
            raise PermissionError(f"File is not readable: {file_path}")

    @staticmethod
    def validate_file_size(file_path: str) -> None:
        """Valida tamaño del archivo."""
        file_size = os.path.getsize(file_path)
        if file_size > MAX_FILE_SIZE:
            raise ValueError(
                f"File too large: {file_size} bytes (max: {MAX_FILE_SIZE})"
            )

        if file_size == 0:
            raise ValueError("File is empty")

    @staticmethod
    def validate_file_extension(file_path: str) -> str:
        """Valida extensión y retorna la extensión."""
        extension = Path(file_path).suffix.lower()
        if extension not in ALLOWED_EXTENSIONS:
            raise ValueError(f"File extension not allowed: {extension}")
        return extension

    @staticmethod
    def validate_mime_type(file_path: str) -> None:
        """Valida MIME type del archivo."""
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type not in ALLOWED_MIME_TYPES:
            raise ValueError(f"MIME type not allowed: {mime_type}")

    @staticmethod
    def sanitize_content(content: str) -> str:
        """Sanitiza contenido extraído."""
        if not content or not content.strip():
            raise ValueError("Extracted content is empty")

        # Remove harmful characters
        sanitized = content.replace("\x00", "")
        sanitized = "".join(
            char for char in sanitized if ord(char) >= 32 or char in "\n\r\t"
        )

        # Limit content size
        if len(sanitized) > MAX_CONTENT_SIZE:
            sanitized = sanitized[:MAX_CONTENT_SIZE] + "\n[... content truncated ...]"

        return sanitized.strip()

    @classmethod
    def validate_all(cls, file_path: str) -> str:
        """Ejecuta todas las validaciones y retorna extensión."""
        cls.validate_file_path(file_path)
        cls.validate_file_size(file_path)
        cls.validate_mime_type(file_path)
        return cls.validate_file_extension(file_path)
