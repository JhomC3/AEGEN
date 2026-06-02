# tests/unit/personality/test_style_analyzer.py

from src.personality.style_analyzer import StyleAnalyzer


class TestStyleAnalyzer:
    """Tests unitarios para StyleAnalyzer."""

    def test_detect_language_spanish(self) -> None:
        """Detecta español en mensaje corto."""
        analyzer = StyleAnalyzer()
        result = analyzer.analyze(["Hola, cómo estás?"])
        assert result is not None
        assert result.detected_language == "es"

    def test_detect_language_english(self) -> None:
        """Detecta inglés en mensaje corto."""
        analyzer = StyleAnalyzer()
        result = analyzer.analyze(["Hello, how are you?"])
        assert result is not None
        assert result.detected_language == "en"

    def test_detect_language_portuguese(self) -> None:
        """Detecta portugués en mensaje corto."""
        analyzer = StyleAnalyzer()
        result = analyzer.analyze(["Olá, como você está?"])
        assert result is not None
        assert result.detected_language == "pt"

    def test_detect_formality_muy_formal(self) -> None:
        """Detecta formalidad muy alta."""
        analyzer = StyleAnalyzer()
        result = analyzer.analyze([
            "Estimado señor, quisiera atentamente solicitar su atención"
        ])
        assert result is not None
        assert result.formality_indicator == "muy_formal"

    def test_detect_formality_muy_casual(self) -> None:
        """Detecta formalidad muy baja."""
        analyzer = StyleAnalyzer()
        result = analyzer.analyze(["q onda güey, xq no vienes"])
        assert result is not None
        assert result.formality_indicator == "muy_casual"

    def test_detect_brevity_telegraphic(self) -> None:
        """Detecta brevedad telegráfica."""
        analyzer = StyleAnalyzer()
        result = analyzer.analyze(["Ok", "Sí", "No"])
        assert result is not None
        assert result.brevity == "telegrafico"

    def test_detect_brevity_verbose(self) -> None:
        """Detecta verbosidad."""
        analyzer = StyleAnalyzer()
        long_message = "A" * 150
        result = analyzer.analyze([long_message])
        assert result is not None
        assert result.brevity == "verboso"

    def test_detect_emoji_true(self) -> None:
        """Detecta presencia de emojis."""
        analyzer = StyleAnalyzer()
        result = analyzer.analyze(["Hola 😊"])
        assert result is not None
        assert result.uses_emoji is True

    def test_detect_emoji_false(self) -> None:
        """Detecta ausencia de emojis."""
        analyzer = StyleAnalyzer()
        result = analyzer.analyze(["Hola, como estas"])
        assert result is not None
        assert result.uses_emoji is False

    def test_analyze_empty_messages(self) -> None:
        """Retorna None si no hay mensajes."""
        analyzer = StyleAnalyzer()
        result = analyzer.analyze([])
        assert result is None
