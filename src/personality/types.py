from dataclasses import dataclass, field


@dataclass
class PersonalityAdaptation:
    """Parámetros de personalidad que evolucionan por usuario."""

    preferred_style: str = "casual"
    communication_level: str = "intermediate"
    humor_tolerance: float = 0.7
    formality_level: float = 0.3
    learned_preferences: list[str] = field(default_factory=list)
    active_topics: list[str] = field(default_factory=list)


@dataclass
class SkillOverlay:
    """Modificador de personalidad para un skill específico."""

    name: str
    tone_modifiers: str
    instructions: str
    anti_patterns: str | None = None


@dataclass
class PersonalityBase:
    """Identidad y Alma base de MAGI."""

    identity: dict[str, str]
    soul: str
