"""Cargador dinámico de skills desde filesystem."""

from __future__ import annotations

import importlib.util
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from langchain_core.tools import BaseTool

from src.core.schemas.skills import SkillContent
from src.personality.skill_parser import parse_skill_md

logger = logging.getLogger(__name__)


@dataclass
class LoadedSkill:
    """Un skill completamente cargado y listo para registro."""

    content: SkillContent
    tool: BaseTool | None = None
    tool_module: Any = None
    schemas_module: Any = None
    path: Path = field(default_factory=Path)


class SkillLoader:
    """Descubre y carga skills desde directorios del filesystem."""

    def __init__(self, skill_dirs: list[Path] | None = None) -> None:
        # Por defecto buscamos en core y en storage
        self._skill_dirs = skill_dirs or [
            Path("src/personality/skills"),
            Path("storage/skills"),
        ]

    async def discover_and_load(self) -> list[LoadedSkill]:
        """Escanea todos los directorios de skills y carga los válidos."""
        loaded: list[LoadedSkill] = []
        seen_ids: set[str] = set()

        for base_dir in self._skill_dirs:
            if not base_dir.exists():
                logger.debug("Directorio de skills no encontrado: %s", base_dir)
                continue

            # Escanear subdirectorios (cada uno es un potencial skill)
            for skill_dir in sorted(base_dir.iterdir()):
                if not skill_dir.is_dir() or skill_dir.name.startswith((".", "_")):
                    continue

                skill_md = skill_dir / "SKILL.md"
                if not skill_md.exists():
                    continue

                try:
                    skill = await self._load_single(skill_dir)
                    skill_id = skill.content.manifest.id

                    if skill_id in seen_ids:
                        logger.warning(
                            "ID de skill duplicado '%s' en %s. Ignorando.",
                            skill_id,
                            skill_dir,
                        )
                        continue

                    seen_ids.add(skill_id)
                    loaded.append(skill)
                    logger.info(
                        "Skill cargado exitosamente: %s (v%s)",
                        skill_id,
                        skill.content.manifest.version,
                    )
                except Exception:
                    logger.exception("Error cargando skill desde %s", skill_dir)

        return loaded

    async def _load_single(self, skill_dir: Path) -> LoadedSkill:
        """Carga un único skill desde su directorio."""
        skill_md_path = skill_dir / "SKILL.md"
        content_text = skill_md_path.read_text(encoding="utf-8")
        content = parse_skill_md(content_text)

        # Intentar cargar tools.py
        tool, module = self._load_tool_module(skill_dir)

        # Intentar cargar schemas.py (opcional)
        schemas_module = self._load_module(
            skill_dir / "schemas.py", f"skill_{skill_dir.name}_schemas"
        )

        return LoadedSkill(
            content=content,
            tool=tool,
            tool_module=module,
            schemas_module=schemas_module,
            path=skill_dir,
        )

    def _load_tool_module(self, skill_dir: Path) -> tuple[BaseTool | None, Any]:
        """Intenta importar tools.py y extraer el tool principal."""
        tools_py = skill_dir / "tools.py"
        if not tools_py.exists():
            return None, None

        module_name = f"skill_{skill_dir.name}_tools"
        module = self._load_module(tools_py, module_name)

        if module:
            # Convención: el tool principal se exporta como SKILL_TOOL
            tool = getattr(module, "SKILL_TOOL", None)
            return tool, module

        return None, None

    def _load_module(self, file_path: Path, module_name: str) -> Any:
        """Carga un archivo Python como módulo dinámico."""
        if not file_path.exists():
            return None

        try:
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if spec is None or spec.loader is None:
                return None

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
        except Exception:
            logger.exception("Error importando módulo dinámico: %s", file_path)
            return None
