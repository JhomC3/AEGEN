# tests/unit/memory/test_global_knowledge_loader.py
from pathlib import Path

from src.memory.global_knowledge_loader import GlobalKnowledgeLoader


class TestShouldProcessFile:
    """Verifica el filtro de seguridad de archivos globales."""

    def setup_method(self):
        self.loader = GlobalKnowledgeLoader.__new__(GlobalKnowledgeLoader)
        self.loader.knowledge_path = Path("/tmp/test_knowledge")

    def test_core_prefix_bypasses_numeric_filter(self):
        """CORE_ con ISBN debe ser aceptado (causa raíz del bug v0.7.2)."""
        path = Path("CORE_Unified_Protocol_9780190685973.pdf")
        should_process, reason = self.loader._should_process_file(path)
        assert should_process is True
        assert reason == "aceptado"

    def test_core_prefix_case_insensitive(self):
        """core_ en minúsculas también debe funcionar."""
        path = Path("core_guia_esencial.pdf")
        should_process, reason = self.loader._should_process_file(path)
        assert should_process is True

    def test_user_id_file_rejected(self):
        """Archivo con ID de usuario largo (no CORE_) debe ser rechazado."""
        path = Path("123456789_chat_export.txt")
        should_process, reason = self.loader._should_process_file(path)
        assert should_process is False
        assert "id_usuario" in reason

    def test_legacy_keywords_rejected(self):
        """Archivos con keywords legacy deben ser rechazados."""
        for name in [
            "buffer_export.txt",
            "user_summary.md",
            "vault_data.txt",
            "profile_backup.pdf",
        ]:
            path = Path(name)
            should_process, reason = self.loader._should_process_file(path)
            assert should_process is False, f"{name} debería ser rechazado"
            assert "keyword" in reason

    def test_unsupported_extension_rejected(self):
        """Extensiones no soportadas deben ser rechazadas."""
        path = Path("notes.docx")
        should_process, reason = self.loader._should_process_file(path)
        assert should_process is False
        assert "extension" in reason

    def test_valid_text_file_accepted(self):
        """Archivo de texto normal debe ser aceptado."""
        path = Path("guia_practica.txt")
        should_process, reason = self.loader._should_process_file(path)
        assert should_process is True

    def test_valid_markdown_accepted(self):
        """Archivo markdown debe ser aceptado."""
        path = Path("reference_guide.md")
        should_process, reason = self.loader._should_process_file(path)
        assert should_process is True

    def test_returns_tuple(self):
        """Siempre retorna una tupla (bool, str)."""
        path = Path("test.pdf")
        result = self.loader._should_process_file(path)
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], bool)
        assert isinstance(result[1], str)
