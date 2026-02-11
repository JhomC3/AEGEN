# src/core/schemas/profile.py
"""
Pydantic models for the AEGEN user profile.

These models define the canonical structure of a user profile. When loading
old profiles from Redis/SQLite that lack newer sections, Pydantic fills in
defaults automatically via model_validate().
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class CrisisContact(BaseModel):
    name: str
    relation: str
    how_to_reach: str = ""


class SupportPreferences(BaseModel):
    """How the user wants to be supported."""

    response_style: Literal["direct", "soft", "balanced"] = "balanced"
    prefers_humor: bool | None = None
    prefers_exploration: bool = True
    topics_to_avoid: list[str] = Field(default_factory=list)
    preferred_techniques: list[str] = Field(default_factory=list)
    crisis_contacts: list[CrisisContact] = Field(default_factory=list)


class CopingMechanisms(BaseModel):
    """User-reported strengths and triggers."""

    known_strengths: list[str] = Field(default_factory=list)
    known_triggers: list[str] = Field(default_factory=list)
    calming_anchors: list[str] = Field(default_factory=list)


class MemorySettings(BaseModel):
    """User consent and memory behavior preferences."""

    consent_given: bool = True
    ephemeral_mode: bool = False
    sensitivity_threshold: Literal["low", "medium", "high"] = "medium"


class ClinicalSafety(BaseModel):
    """Clinical guardrails metadata."""

    disclaimer_shown: bool = False
    last_risk_assessment: str | None = None
    escalation_protocol: Literal["passive", "active"] = "passive"
    emergency_resources: list[str] = Field(
        default_factory=lambda: [
            "Línea 106 (Colombia) - Línea de orientación",
            "Emergencias: 911",
        ]
    )


class Identity(BaseModel):
    name: str = "Usuario"
    style: str = "Casual y Directo"
    preferences: dict[str, Any] = Field(default_factory=dict)


class PersonalityAdaptation(BaseModel):
    preferred_style: str = "casual"
    communication_level: str = "intermediate"
    humor_tolerance: float = 0.7
    formality_level: float = 0.3
    history_limit: int = 20
    learned_preferences: list[str] = Field(default_factory=list)
    active_topics: list[str] = Field(default_factory=list)


class PsychologicalState(BaseModel):
    current_phase: str = "Discovery"
    key_metaphors: list[str] = Field(default_factory=list)
    active_struggles: list[str] = Field(default_factory=list)


class ValuesAndGoals(BaseModel):
    core_values: list[str] = Field(default_factory=list)
    short_term_goals: list[str] = Field(default_factory=list)
    long_term_dreams: list[str] = Field(default_factory=list)
    physical_state: str = "Not specified"


class TasksAndActivities(BaseModel):
    active_tasks: list[str] = Field(default_factory=list)
    completed_activities: list[str] = Field(default_factory=list)


class Evolution(BaseModel):
    level: int = 1
    milestones_count: int = 0
    path_traveled: list[dict[str, Any]] = Field(default_factory=list)


class Localization(BaseModel):
    country_code: str | None = None
    region: str | None = None
    timezone: str = "UTC"
    language_code: str | None = None
    dialect: str = "neutro"
    dialect_hint: str | None = None
    confirmed_by_user: bool = False


class TimelineEntry(BaseModel):
    date: str
    event: str
    type: str = "system"


class ProfileMetadata(BaseModel):
    version: str = "1.2.0"
    last_updated: str = Field(default_factory=lambda: datetime.now().isoformat())


class UserProfile(BaseModel):
    """
    Root profile model. All fields have defaults so that model_validate()
    on an old dict automatically fills in new sections.
    """

    identity: Identity = Field(default_factory=Identity)
    personality_adaptation: PersonalityAdaptation = Field(
        default_factory=PersonalityAdaptation
    )
    psychological_state: PsychologicalState = Field(default_factory=PsychologicalState)
    values_and_goals: ValuesAndGoals = Field(default_factory=ValuesAndGoals)
    tasks_and_activities: TasksAndActivities = Field(default_factory=TasksAndActivities)
    evolution: Evolution = Field(default_factory=Evolution)
    active_tags: list[str] = Field(default_factory=lambda: ["bienvenida"])
    localization: Localization = Field(default_factory=Localization)
    timeline: list[TimelineEntry] = Field(
        default_factory=lambda: [
            TimelineEntry(
                date=datetime.now().isoformat(), event="Creación de Perfil Evolutivo"
            ),
        ]
    )
    metadata: ProfileMetadata = Field(default_factory=ProfileMetadata)
    # New enrichment sections
    support_preferences: SupportPreferences = Field(default_factory=SupportPreferences)
    coping_mechanisms: CopingMechanisms = Field(default_factory=CopingMechanisms)
    memory_settings: MemorySettings = Field(default_factory=MemorySettings)
    clinical_safety: ClinicalSafety = Field(default_factory=ClinicalSafety)

    model_config = {"extra": "allow"}
