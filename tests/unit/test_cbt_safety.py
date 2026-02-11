# tests/unit/test_cbt_safety.py

from src.agents.specialists.cbt_specialist import (
    _build_enriched_profile_context,
    format_knowledge_for_prompt,
)


class TestFormatKnowledge:
    def test_filters_inactive_inferred_data(self):
        """Knowledge items with source_type='inferred' and no confirmation should be marked."""
        knowledge = {
            "entities": [
                {
                    "name": "Max",
                    "type": "mascota",
                    "attributes": {},
                    "source_type": "explicit",
                    "confidence": 1.0,
                },
                {
                    "name": "catastrofización",
                    "type": "patrón_cognitivo",
                    "attributes": {},
                    "source_type": "inferred",
                    "confidence": 0.6,
                },
            ],
        }
        result = format_knowledge_for_prompt(knowledge)
        assert "Max" in result
        assert "(hipótesis" in result.lower() or "inferido" in result.lower()


class TestEnrichedProfileContext:
    def test_includes_support_preferences(self):
        profile = {
            "support_preferences": {
                "response_style": "soft",
                "topics_to_avoid": ["familia"],
                "preferred_techniques": ["respiración"],
            },
            "coping_mechanisms": {
                "known_strengths": ["caminar", "escribir"],
                "calming_anchors": ["música clásica"],
            },
            "clinical_safety": {
                "escalation_protocol": "passive",
                "emergency_resources": ["Línea 106", "911"],
            },
        }
        context = _build_enriched_profile_context(profile)
        assert "soft" in context
        assert "familia" in context
        assert "caminar" in context
        assert "música clásica" in context

    def test_handles_empty_profile(self):
        """Must not crash on minimal/empty profile."""
        profile = {}
        context = _build_enriched_profile_context(profile)
        assert isinstance(context, str)
