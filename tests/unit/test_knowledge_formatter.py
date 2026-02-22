# tests/unit/test_knowledge_formatter.py
from src.agents.utils.knowledge_formatter import format_knowledge_for_prompt


class TestKnowledgeFormatterProvenance:
    """Verifica que hechos inferidos se excluyen del prompt."""

    def test_explicit_facts_included(self):
        knowledge = {
            "entities": [
                {
                    "name": "Python",
                    "type": "lenguaje",
                    "attributes": {},
                    "source_type": "explicit",
                    "confidence": 1.0,
                }
            ]
        }
        result = format_knowledge_for_prompt(knowledge)
        assert "Python" in result

    def test_inferred_facts_excluded(self):
        """Hechos inferidos legacy NO deben llegar al prompt del LLM."""
        knowledge = {
            "relationships": [
                {
                    "person": "ex-novia inventada",
                    "relation": "ex-pareja",
                    "attributes": {},
                    "source_type": "inferred",
                    "confidence": 0.6,
                }
            ]
        }
        result = format_knowledge_for_prompt(knowledge)
        assert "ex-novia" not in result

    def test_low_confidence_explicit_excluded(self):
        knowledge = {
            "entities": [
                {
                    "name": "dato dudoso",
                    "type": "x",
                    "attributes": {},
                    "source_type": "explicit",
                    "confidence": 0.4,
                }
            ]
        }
        result = format_knowledge_for_prompt(knowledge)
        assert "dato dudoso" not in result

    def test_empty_after_filter(self):
        knowledge = {
            "entities": [
                {
                    "name": "x",
                    "type": "y",
                    "attributes": {},
                    "source_type": "inferred",
                    "confidence": 0.3,
                }
            ]
        }
        result = format_knowledge_for_prompt(knowledge)
        assert result == "No hay hechos confirmados aún."
