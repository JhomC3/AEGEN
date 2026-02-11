from typing import Any


def format_knowledge_for_prompt(knowledge: dict[str, Any]) -> str:
    """
    Formatea la Bóveda de Conocimiento marcando inferencias.
    Versión unificada para todos los especialistas.
    """
    sections = []

    def fmt_attrs(attrs: dict) -> str:
        """Helper para formatear atributos de forma limpia."""
        if not attrs:
            return ""
        return ", ".join([f"{k}={v}" for k, v in attrs.items()])

    def provenance_tag(item: dict) -> str:
        if item.get("source_type") == "inferred":
            conf = item.get("confidence", 0.5)
            return f" (hipótesis, confianza: {conf:.0%})"
        return ""

    if knowledge.get("entities"):
        ents = "\n".join([
            f"- {e['name']} ({e['type']}): {fmt_attrs(e.get('attributes', {}))}"
            f"{provenance_tag(e)}"
            for e in knowledge["entities"]
        ])
        sections.append(f"ENTIDADES:\n{ents}")

    if knowledge.get("medical"):
        meds = "\n".join([
            f"- {m['name']} ({m['type']}): {m.get('details', '')}{provenance_tag(m)}"
            for m in knowledge["medical"]
        ])
        sections.append(f"DATOS MÉDICOS:\n{meds}")

    if knowledge.get("relationships"):
        rels = "\n".join([
            f"- {r['person']} ({r['relation']}): {fmt_attrs(r.get('attributes', {}))}"
            f"{provenance_tag(r)}"
            for r in knowledge["relationships"]
        ])
        sections.append(f"RELACIONES:\n{rels}")

    if knowledge.get("preferences"):
        prefs = "\n".join([
            f"- {p['category']}: {p['value']}{provenance_tag(p)}"
            for p in knowledge["preferences"]
        ])
        sections.append(f"PREFERENCIAS:\n{prefs}")

    return "\n\n".join(sections) if sections else "No hay hechos confirmados aún."
