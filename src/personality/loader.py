import logging
import re
from pathlib import Path

import aiofiles

from src.personality.types import PersonalityBase, SkillOverlay

logger = logging.getLogger(__name__)


class PersonalityLoader:
    """Carga y parsea archivos Markdown de personalidad."""

    def __init__(self, base_path: str = "src/personality/") -> None:
        self.base_path = Path(base_path)

    async def load_base(self) -> PersonalityBase:
        """Carga IDENTITY.md y SOUL.md."""
        identity_path = self.base_path / "base" / "IDENTITY.md"
        soul_path = self.base_path / "base" / "SOUL.md"

        identity = await self._parse_identity(identity_path)
        soul = await self._read_file(soul_path)

        return PersonalityBase(identity=identity, soul=soul)

    async def load_skill_overlay(self, skill_name: str) -> SkillOverlay | None:
        """Carga un overlay de skill específico."""
        overlay_path = self.base_path / "skills" / f"{skill_name}_overlay.md"
        if not overlay_path.exists():
            # Fallback a chat si no existe
            overlay_path = self.base_path / "skills" / "chat_overlay.md"
            if not overlay_path.exists():
                return None

        content = await self._read_file(overlay_path)
        return self._parse_overlay(skill_name, content)

    async def _read_file(self, path: Path) -> str:
        if not path.exists():
            logger.warning(f"Archivo de personalidad no encontrado: {path}")
            return ""
        async with aiofiles.open(path, encoding="utf-8") as f:
            return await f.read()

    async def _parse_identity(self, path: Path) -> dict[str, str]:
        content = await self._read_file(path)
        identity = {}
        # Extraer items de lista: - **Key:** Value
        pattern = r"-\s*\*\*([^*]+)\*\*:\s*(.*)"
        matches = re.findall(pattern, content)
        for key, value in matches:
            identity[key.strip().lower()] = value.strip()
        return identity

    def _parse_overlay(self, name: str, content: str) -> SkillOverlay:
        """Parsea secciones del overlay."""
        tone_modifiers = self._extract_section(content, "Tone Modifiers")
        instructions = self._extract_section(content, "Instructions")
        anti_patterns = self._extract_section(content, "Anti-Patterns Específicos")

        return SkillOverlay(
            name=name,
            tone_modifiers=tone_modifiers,
            instructions=instructions,
            anti_patterns=anti_patterns,
        )

    def _extract_section(self, content: str, section_name: str) -> str:
        """Extrae contenido bajo un encabezado ##."""
        pattern = rf"## {section_name}\n(.*?)(?=\n## |\Z)"
        match = re.search(pattern, content, re.DOTALL)
        return match.group(1).strip() if match else ""
