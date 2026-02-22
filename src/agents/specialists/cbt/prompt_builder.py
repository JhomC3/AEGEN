from typing import Any


def build_enriched_profile_context(profile: dict[str, Any]) -> str:
    """Formats enriched profile sections for the CBT system prompt."""
    sections = []

    sp = profile.get("support_preferences", {})
    if sp:
        parts = [f"Estilo preferido: {sp.get('response_style', 'balanced')}"]
        if sp.get("topics_to_avoid"):
            parts.append(f"Temas a evitar: {', '.join(sp['topics_to_avoid'])}")
        if sp.get("preferred_techniques"):
            parts.append(
                f"Técnicas preferidas: {', '.join(sp['preferred_techniques'])}"
            )
        sections.append(
            "[PREFERENCIAS DE APOYO]\n" + "\n".join(f"- {p}" for p in parts)
        )

    cm = profile.get("coping_mechanisms", {})
    if cm:
        parts = []
        if cm.get("known_strengths"):
            parts.append(f"Fortalezas: {', '.join(cm['known_strengths'])}")
        if cm.get("calming_anchors"):
            parts.append(f"Anclajes de calma: {', '.join(cm['calming_anchors'])}")
        if parts:
            sections.append(
                "[RECURSOS DEL USUARIO]\n" + "\n".join(f"- {p}" for p in parts)
            )

    cs = profile.get("clinical_safety", {})
    if cs:
        resources = cs.get("emergency_resources", [])
        if resources:
            sections.append(
                "[RECURSOS DE EMERGENCIA]\n" + "\n".join(f"- {r}" for r in resources)
            )

    return "\n\n".join(sections) if sections else ""


def build_routing_instructions(next_actions: list[str]) -> str:
    """Helper para construir instrucciones de enrutamiento."""
    if not next_actions:
        return ""

    instructions = "\n\nINSTRUCCIONES DE ENRUTAMIENTO PRIORITARIAS:\n"
    mapping = {
        "depth_empathy": ("- Prioriza la validación emocional y la compañía.\n"),
        "clarify_emotional_state": (
            "- El usuario no es claro. Invítalo amablemente a contar más.\n"
        ),
        "active_listening": (
            "- Demuestra que lo estás escuchando. Parafrasea de forma natural.\n"
        ),
        "gentle_probe": ("- Explora suavemente qué le preocupa, sin interrogar.\n"),
        "pacing_one_step": (
            "- PACING: Haz MÁXIMO 1 pregunta corta. No intentes avanzar rápido.\n"
        ),
        "handle_resistance": (
            "- El usuario siente frustración. Valídalo y dale espacio.\n"
        ),
        "validate_frustration": (
            "- Reconoce explícitamente su frustración como válida y comprensible.\n"
        ),
    }

    for action in next_actions:
        if action in mapping:
            instructions += mapping[action]

    return instructions


CLINICAL_GUARDRAILS = (
    "\n\n[GUARDRAILS ESTRICTOS DE PERSONALIDAD]\n"
    "- NUNCA uses lenguaje diagnóstico ni hables de 'TCC' o 'distorsiones'.\n"
    "- Eres su amigo, no terapeuta. Acompáñalo como lo haría un amigo tomando café.\n"
    "- NUNCA le digas 'busca ayuda profesional' salvo crisis explícita y grave.\n"
    "- Los datos '(hipótesis)' son inferencias no confirmadas. Úsalos con sutileza.\n"
    "- **Pacing:** Da 1 paso a la vez. Haz MÁXIMO 1 pregunta por mensaje.\n"
)
