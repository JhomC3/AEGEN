import re

from src.personality.types import StyleSignals


class StyleAnalyzer:
    """
    Analiza el estilo conversacional del usuario mediante heurísticas en Python.
    No detecta dialecto, solo forma (formalidad, brevedad, idioma base).
    """

    def analyze(self, recent_messages: list[str]) -> StyleSignals | None:
        """
        Analiza los últimos mensajes para extraer señales de estilo.
        Retorna None si no hay mensajes suficientes.
        """
        if not recent_messages:
            return None

        full_text_raw = " ".join(recent_messages)
        full_text_lower = full_text_raw.lower()

        return StyleSignals(
            detected_language=self._detect_language(full_text_lower),
            formality_indicator=self._detect_formality(full_text_raw, full_text_lower),
            brevity=self._detect_brevity(recent_messages),
            uses_emoji=self._detect_emoji(full_text_lower),
        )

    def _detect_language(self, text: str) -> str:
        """Detección ultra-ligera de idioma por palabras clave discriminantes."""
        keywords = {
            "en": [" the ", " with ", " is ", " and ", " are "],
            "pt": [
                " com ",
                " você ",
                " então ",
                " mas ",
            ],  # Evitar " o ", " a " que son comunes en es
            "fr": [" le ", " la ", " les ", " et ", " avec "],
        }

        for lang, words in keywords.items():
            if any(w in text for w in words):
                return lang
        return "es"  # Default

    def _detect_formality(self, raw_text: str, lower_text: str) -> str:
        """Detecta nivel de formalidad."""
        # Indicadores formales
        formal_markers = [
            "usted",
            "estimado",
            "quisiera",
            "atentamente",
            "podría",
            "podria",
        ]
        # Indicadores casuales
        casual_markers = [
            " q ",
            " xq ",
            " pa ",
            "jaja",
            "lol",
            "hey",
            "che",
            "güey",
            "parce",
        ]

        formal_score = sum(1 for m in formal_markers if m in lower_text)
        casual_score = sum(1 for m in casual_markers if m in lower_text)

        # Matiz por Capitalization (señal de formalidad)
        # Si usa mayúsculas al inicio y puntuación, sumamos puntos.
        if re.search(r"[A-Z][a-z]+[\.!\?]", raw_text):
            formal_score += 1

        # Matiz por total minúsculas (señal casual)
        if raw_text == lower_text and len(raw_text) > 20:
            casual_score += 1

        if formal_score > casual_score:
            return "formal" if formal_score < 3 else "muy_formal"
        if casual_score > formal_score:
            return "casual" if casual_score < 3 else "muy_casual"
        return "casual"  # Default balanceado

    def _detect_brevity(self, messages: list[str]) -> str:
        """Analiza la longitud promedio de los mensajes."""
        avg_len = sum(len(m) for m in messages) / len(messages)

        if avg_len < 30:
            return "telegrafico"
        if avg_len < 120:
            return "conciso"
        return "verboso"

    def _detect_emoji(self, text: str) -> bool:
        """Detección simple de presencia de emojis o emoticonos."""
        # Regex básica para emojis y emoticonos comunes
        emoji_pattern = r"[\U00010000-\U0010ffff]|[:;=]-?[)D(|P]"
        return bool(re.search(emoji_pattern, text))


# Instancia global única
style_analyzer = StyleAnalyzer()
