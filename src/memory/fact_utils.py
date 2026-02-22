# src/memory/fact_utils.py
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


def get_identity_key(item: dict[str, Any], category: str) -> str:
    """Returns a dedup key based on the semantic identity of a fact."""
    if category == "entities":
        return f"{item.get('name', '')}::{item.get('type', '')}".lower()
    if category == "relationships":
        return f"{item.get('person', '')}::{item.get('relation', '')}".lower()
    if category == "medical":
        return f"{item.get('name', '')}::{item.get('type', '')}".lower()
    if category == "preferences":
        return f"{item.get('category', '')}::{item.get('value', '')}".lower()
    if category == "milestones":
        return f"{item.get('description', '')}".lower()
    return json.dumps(item, sort_keys=True)


def merge_fact_knowledge(old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    """Merges new knowledge into old, deduplicating by semantic identity."""
    merged = old.copy()

    # Merge explícito del nombre de usuario
    if new.get("user_name"):
        merged["user_name"] = new["user_name"]

    categories = ("entities", "preferences", "medical", "relationships", "milestones")
    for key in categories:
        _merge_category(merged, new, key)

    return merged


def _merge_category(merged: dict[str, Any], new: dict[str, Any], key: str) -> None:
    """Helper to merge a specific category of facts, filtering unsafe data."""
    if key not in merged:
        merged[key] = []

    # Index existing items by identity key
    existing: dict[str, int] = {
        get_identity_key(item, key): idx for idx, item in enumerate(merged[key])
    }

    for item in new.get(key, []):
        # FILTRO ANTI-ALUCINACIÓN
        if item.get("source_type") == "inferred":
            continue

        if item.get("confidence", 0) < 0.8:
            continue

        ik = get_identity_key(item, key)
        if ik in existing:
            # Update existing item
            old_item = merged[key][existing[ik]]
            if isinstance(old_item.get("attributes"), dict) and isinstance(
                item.get("attributes"), dict
            ):
                old_item["attributes"].update(item["attributes"])

            # Overwrite with new data if same/higher confidence
            if item.get("confidence", 0) >= old_item.get("confidence", 0):
                fields = ("source_type", "confidence", "evidence", "sensitivity")
                for field in fields:
                    if field in item:
                        old_item[field] = item[field]
        else:
            merged[key].append(item)
            existing[ik] = len(merged[key]) - 1
