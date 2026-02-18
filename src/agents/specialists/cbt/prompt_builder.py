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
        "depth_empathy": ("- Prioriza la validación emocional profunda.\n"),
        "clarify_emotional_state": (
            "- Estado ambiguo. Haz una pregunta suave para clarificar.\n"
        ),
        "active_listening": ("- Usa escucha activa reflexiva. Parafrasea.\n"),
        "gentle_probe": ("- Indaga sobre pensamientos automáticos subyacentes.\n"),
    }

    for action in next_actions:
        if action in mapping:
            instructions += mapping[action]

    return instructions


CLINICAL_GUARDRAILS = (
    "\n\n[GUARDRAILS CLÍNICOS]\n"
    "- NUNCA uses lenguaje diagnóstico.\n"
    "- Puedes decir 'lo que describes suena a lo que en psicología se llama..., "
    "pero solo un profesional puede evaluarlo'.\n"
    "- Si el usuario pide diagnóstico, prescripción o evaluación, "
    "declina y sugiere buscar un profesional.\n"
    "- Si detectas riesgo de autolesión o crisis, muestra los recursos "
    "y sugiere contactar a un profesional inmediatamente.\n"
    "- Los datos marcados como '(hipótesis)' en el conocimiento son "
    "inferencias no confirmadas. Úsalos con precaución.\n"
)
