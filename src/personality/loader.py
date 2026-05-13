import logging
import re
from pathlib import Path

import aiofiles

from src.personality.skill_parser import parse_skill_md
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

    async def load_skill(self, skill_name: str) -> SkillOverlay | None:
        """
        Carga un skill buscando primero en el nuevo formato de directorio
        y luego en el legacy overlay file.
        """
        # 1. Intentar nuevo formato: skills/{name}/SKILL.md
        new_path = self.base_path / "skills" / skill_name / "SKILL.md"
        if new_path.exists():
            content = await self._read_file(new_path)
            parsed = parse_skill_md(content)
            # Adaptamos SkillContent a SkillOverlay para retrocompatibilidad
            return SkillOverlay(
                name=parsed.manifest.name,
                tone_modifiers=parsed.tone_modifiers,
                instructions=parsed.instructions,
                anti_patterns=parsed.anti_patterns,
                linguistic_rules=parsed.linguistic_rules,
            )

        # 2. Intentar formato legacy: skills/{name}_overlay.md
        legacy_path = self.base_path / "skills" / f"{skill_name}_overlay.md"
        if legacy_path.exists():
            logger.info("Cargando skill '%s' desde formato legacy overlay", skill_name)
            content = await self._read_file(legacy_path)
            return self._parse_overlay(skill_name, content)

        # 3. Fallback a chat si es un skill desconocido
        if skill_name != "chat":
            return await self.load_skill("chat")

        return None

    async def load_skill_overlay(self, skill_name: str) -> SkillOverlay | None:
        """Método legacy para mantener compatibilidad."""
        return await self.load_skill(skill_name)

    async def _read_file(self, path: Path) -> str:
        if not path.exists():
            logger.warning("Archivo de personalidad no encontrado: %s", path)
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
        """Parsea secciones del overlay legacy."""
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
