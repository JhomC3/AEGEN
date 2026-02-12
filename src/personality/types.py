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
class StyleSignals:
    """Señales de estilo detectadas en mensajes recientes."""

    detected_language: str  # "es", "en", "pt", etc.
    formality_indicator: str  # "muy_formal", "formal", "casual", "muy_casual"
    brevity: str  # "telegrafico", "conciso", "verboso"
    uses_emoji: bool


@dataclass
class LinguisticProfile:
    """Perfil lingüístico procesado para inyección en el prompt."""

    dialect: str  # "neutro", "argentino", "colombiano", etc.
    dialect_hint: str | None  # "paisa", "porteño", etc.
    preferred_dialect: str | None  # Preferencia explicita del usuario
    dialect_confirmed: bool  # Si la ubicación fue confirmada por el usuario
    formality_level: float  # 0.0-1.0 del perfil evolutivo
    humor_tolerance: float  # 0.0-1.0 del perfil evolutivo
    preferred_style: str  # "casual", "formal", "tecnico", "empatico"


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
