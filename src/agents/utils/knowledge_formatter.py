from typing import Any

# Umbral mínimo de confianza para mostrar un hecho al LLM
MIN_CONFIDENCE_FOR_PROMPT = 0.7


def format_knowledge_for_prompt(knowledge: dict[str, Any]) -> str:
    """
    Formatea la Bóveda de Conocimiento excluyendo inferencias.
    Solo hechos explícitos con confianza >= 0.7 llegan al LLM.
    """
    sections = []

    def fmt_attrs(attrs: dict) -> str:
        """Helper para formatear atributos de forma limpia."""
        if not attrs:
            return ""
        return ", ".join([f"{k}={v}" for k, v in attrs.items()])

    def is_trusted(item: dict) -> bool:
        """Filtro de procedencia: solo hechos explícitos y confiables."""
        if item.get("source_type") == "inferred":
            return False
        return not item.get("confidence", 1.0) < MIN_CONFIDENCE_FOR_PROMPT

    entities = [e for e in knowledge.get("entities", []) if is_trusted(e)]
    if entities:
        ents = "\n".join([
            f"- {e['name']} ({e['type']}): {fmt_attrs(e.get('attributes', {}))}"
            for e in entities
        ])
        sections.append(f"ENTIDADES:\n{ents}")

    medical = [m for m in knowledge.get("medical", []) if is_trusted(m)]
    if medical:
        meds = "\n".join([
            f"- {m['name']} ({m['type']}): {m.get('details', '')}" for m in medical
        ])
        sections.append(f"DATOS MÉDICOS:\n{meds}")

    relationships = [r for r in knowledge.get("relationships", []) if is_trusted(r)]
    if relationships:
        rels = "\n".join([
            f"- {r['person']} ({r['relation']}): {fmt_attrs(r.get('attributes', {}))}"
            for r in relationships
        ])
        sections.append(f"RELACIONES:\n{rels}")

    preferences = [p for p in knowledge.get("preferences", []) if is_trusted(p)]
    if preferences:
        prefs = "\n".join([f"- {p['category']}: {p['value']}" for p in preferences])
        sections.append(f"PREFERENCIAS:\n{prefs}")

    return "\n\n".join(sections) if sections else "No hay hechos confirmados aún."
