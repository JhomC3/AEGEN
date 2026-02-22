from typing import Literal


def consolidate_fragments(
    fragments: list[dict],
) -> tuple[
    str | None,
    str | None,
    str | None,
    str | None,
    Literal["text", "audio", "document", "image", "unknown"],
]:
    """
    Consolida fragmentos de mensajes en contenido y metadatos únicos.
    Retorna: (content, file_id, language_code, first_name, event_type)
    """
    combined_content = []
    final_file_id = None
    final_language_code = None
    final_first_name = None
    final_event_type: Literal["text", "audio", "document", "image", "unknown"] = "text"

    for frag in fragments:
        if frag.get("content"):
            combined_content.append(frag["content"])
        if not final_language_code and frag.get("language_code"):
            final_language_code = frag["language_code"]
        if not final_first_name and frag.get("first_name"):
            final_first_name = frag["first_name"]

        # Prioridad de tipos
        if frag.get("event_type") == "audio":
            final_file_id = frag.get("file_id")
            final_event_type = "audio"
        elif frag.get("event_type") == "image" and final_event_type != "audio":
            final_file_id = frag.get("file_id")
            final_event_type = "image"

    content = "\n".join(combined_content) if combined_content else None
    return (
        content,
        final_file_id,
        final_language_code,
        final_first_name,
        final_event_type,
    )
