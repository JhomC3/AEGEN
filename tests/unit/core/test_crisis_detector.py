# tests/unit/core/test_crisis_detector.py
from src.core.crisis_detector import detect_crisis


class TestCrisisDetector:
    """Tests unitarios para detect_crisis()."""

    def test_detect_crisis_keywords_positive(self) -> None:
        """Detecta keywords de crisis reales."""
        result = detect_crisis("Quiero suicid y acabar con todo")
        assert result["is_crisis"] is True
        assert result["level"] in ("medium", "high")
        assert len(result["keywords_found"]) > 0

    def test_detect_crisis_metaphor_filtered(self) -> None:
        """Filtra metáforas comunes (no es crisis real)."""
        result = detect_crisis("Me quiero desconectar de las redes sociales")
        assert result["is_crisis"] is False
        assert result["is_metaphor"] is True
        assert result["level"] == "none"

    def test_detect_crisis_metaphor_with_keyword(self) -> None:
        """Si hay keyword + metáfora, prevalece keyword (crisis real)."""
        result = detect_crisis("Me quiero desconectar pero también suicid")
        assert result["is_crisis"] is True
        assert result["is_metaphor"] is False

    def test_detect_crisis_intensifiers(self) -> None:
        """Intensificadores emocionales aumentan confidence."""
        result = detect_crisis("suicid es demasiado, no puedo mas")
        assert result["confidence"] >= 0.7
        assert result["level"] in ("medium", "high")

    def test_detect_crisis_empty_text(self) -> None:
        """Maneja texto vacío sin error."""
        result = detect_crisis("")
        assert result["is_crisis"] is False
        assert result["level"] == "none"

    def test_detect_crisis_low_confidence(self) -> None:
        """Keywords sin intensificadores = low confidence."""
        result = detect_crisis("suicid")
        assert result["level"] == "medium"
        assert result["is_crisis"] is True

    def test_detect_crisis_high_confidence(self) -> None:
        """Múltiples keywords + intensificadores = high confidence."""
        result = detect_crisis("suicid mori acabar")
        # 3 keywords = 0.5 + 0.45 = 0.95 -> high confidence
        assert result["level"] == "high"
        assert result["is_crisis"] is True
