# src/core/schemas/skills.py
from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class SkillRequirements(BaseModel):
    """Requisitos y configuración de un skill."""

    tools: list[str] = Field(default_factory=list)
    memory_access: str = "full"  # "full" | "read_only" | "none"
    priority: int = Field(default=5, ge=0, le=100)
    update_history: bool = True
    chain_to: str | None = None


class SkillGatingRequirements(BaseModel):
    """Requisitos de gating condicional para carga de skills."""

    env: list[str] = Field(default_factory=list)
    python_packages: list[str] = Field(default_factory=list)
    bins: list[str] = Field(default_factory=list)


class SkillSchedule(BaseModel):
    """Configuración de ejecución programada de un skill."""

    cron: str  # Expresión cron
    description: str = ""
    enabled: bool = True


class SkillManifest(BaseModel):
    """Metadatos parseados del frontmatter YAML de un SKILL.md."""

    name: str
    id: str
    version: str = "1.0.0"
    capabilities: list[str] = Field(default_factory=list)
    requirements: SkillRequirements = Field(default_factory=SkillRequirements)
    requires: SkillGatingRequirements = Field(default_factory=SkillGatingRequirements)
    async_capable: bool = False
    schedule: SkillSchedule | None = None

    @field_validator("id")
    @classmethod
    def id_not_empty(cls, v: str) -> str:
        if not v.strip():
            msg = "skill id cannot be empty"
            raise ValueError(msg)
        return v.strip()


class SkillContent(BaseModel):
    """Contenido completo de un skill: manifest + secciones Markdown."""

    manifest: SkillManifest
    tone_modifiers: str = ""
    instructions: str = ""
    anti_patterns: str = ""
    linguistic_rules: str = ""
    raw_sections: dict[str, str] = Field(default_factory=dict)
