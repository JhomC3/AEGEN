from src.personality.types import LinguisticProfile, StyleSignals


def render_dialect_rules(linguistic: LinguisticProfile) -> str:
    """Genera reglas de dialecto basadas en PREFERENCIA > CONFIRMACIÓN > NEUTRO."""
    base = (
        "- **Idioma:** Responde SIEMPRE en el mismo idioma en el que te escribe "
        "el usuario.\n"
    )

    # Prioridad 1: Preferencia Explícita (Highest Priority)
    if linguistic.preferred_dialect:
        return (
            base + f"- **Dialecto ACTIVO:** {linguistic.preferred_dialect}. "
            "Úsalo con naturalidad.\n"
        )

    # Prioridad 2: Ubicación Confirmada (Middle Priority - Sugerencia suave)
    if linguistic.dialect_confirmed and linguistic.dialect != "neutro":
        return base + (
            f"- **Contexto Regional:** El usuario está en {linguistic.dialect}. "
            "Puedes usar modismos locales suaves si él los usa primero, pero NO "
            "fuerces el acento.\n"
        )

    # Default: Neutralidad Cálida (Español Latinoamericano Estándar) + Eco Léxico
    return base + (
        "- **Dialecto Base:** Neutralidad Cálida (Español Latinoamericano "
        "Estándar).\n"
        "- **GUARDRAIL LINGÜÍSTICO:** Prohibido usar voseo ('vos') o modismos de "
        "España ('tío', 'vale'). Usa tuteo neutro ('tú').\n"
        "- **ECO LÉXICO:** Adopta el vocabulario específico del usuario "
        "(sustantivos/verbos) para generar cercanía, pero mantén la gramática "
        "neutra.\n"
    )


def render_style_adaptation(style: StyleSignals | None) -> str:
    """Adapta el tono del prompt según las señales de estilo detectadas."""
    if not style:
        return ""

    rules = ["- **Adaptación de Estilo (Observada):**"]

    # Formalidad
    if style.formality_indicator == "muy_formal":
        rules.append(
            "  * El usuario es MUY FORMAL. Elimina coloquialismos y sé "
            "impecablemente profesional."
        )
    elif style.formality_indicator == "formal":
        rules.append("  * El usuario es formal. Mantén un tono respetuoso.")
    elif style.formality_indicator == "muy_casual":
        rules.append(
            "  * El usuario es MUY CASUAL. Puedes usar mucha jerga y humor relajado."
        )
    else:  # casual
        rules.append("  * El usuario es casual. Sé cercano y relajado.")

    # Brevedad
    if style.brevity == "telegrafico":
        rules.append(
            "  * El usuario es telegráfico. Sé ULTRA-CONCISO, ve directo al grano."
        )
    elif style.brevity == "verboso":
        rules.append(
            "  * El usuario se extiende. Puedes dar respuestas más detalladas y "
            "profundas."
        )

    # Emoji
    if not style.uses_emoji:
        rules.append("  * El usuario NO usa emojis. Reduce su uso al mínimo.")

    return "\n".join(rules) + "\n"
