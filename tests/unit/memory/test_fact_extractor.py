# tests/unit/memory/test_fact_extractor.py
import json

from src.memory.fact_extractor import FactExtractor


class TestFactExtractorOutputFormat:
    def test_extract_json_with_provenance_fields(self):
        """Extracted JSON must include source_type, confidence, evidence, sensitivity per item."""
        extractor = FactExtractor()
        # Simulate what the LLM would return with the new prompt
        llm_output = json.dumps({
            "user_name": "Carlos",
            "entities": [
                {
                    "name": "Max",
                    "type": "mascota",
                    "attributes": {"especie": "perro"},
                    "source_type": "explicit",
                    "confidence": 1.0,
                    "evidence": "mi perro Max",
                    "sensitivity": "low",
                }
            ],
            "preferences": [],
            "medical": [],
            "relationships": [],
            "milestones": [],
        })
        result = extractor._extract_json(llm_output)
        entity = result["entities"][0]
        assert entity["source_type"] == "explicit"
        assert entity["confidence"] == 1.0
        assert entity["evidence"] == "mi perro Max"
        assert entity["sensitivity"] == "low"


class TestMergeKnowledge:
    def test_merge_preserves_provenance(self):
        extractor = FactExtractor()
        old = {
            "entities": [],
            "preferences": [],
            "medical": [],
            "relationships": [],
            "milestones": [],
        }
        new = {
            "entities": [
                {
                    "name": "Max",
                    "type": "mascota",
                    "attributes": {},
                    "source_type": "explicit",
                    "confidence": 1.0,
                    "evidence": "mi perro Max",
                    "sensitivity": "low",
                }
            ],
            "preferences": [],
            "medical": [],
            "relationships": [],
            "milestones": [],
        }
        merged = extractor._merge_knowledge(old, new)
        assert len(merged["entities"]) == 1
        assert merged["entities"][0]["source_type"] == "explicit"

    def test_merge_deduplicates_by_name_and_type(self):
        """If an entity with same name+type exists, update rather than duplicate."""
        extractor = FactExtractor()
        old = {
            "entities": [
                {
                    "name": "Max",
                    "type": "mascota",
                    "attributes": {"raza": "labrador"},
                    "source_type": "explicit",
                    "confidence": 1.0,
                    "evidence": "",
                    "sensitivity": "low",
                }
            ],
            "preferences": [],
            "medical": [],
            "relationships": [],
            "milestones": [],
        }
        new = {
            "entities": [
                {
                    "name": "Max",
                    "type": "mascota",
                    "attributes": {"raza": "labrador", "edad": "3"},
                    "source_type": "explicit",
                    "confidence": 1.0,
                    "evidence": "",
                    "sensitivity": "low",
                }
            ],
            "preferences": [],
            "medical": [],
            "relationships": [],
            "milestones": [],
        }
        merged = extractor._merge_knowledge(old, new)
        # With new merge logic, it should update existing item
        assert len(merged["entities"]) == 1
        assert merged["entities"][0]["attributes"]["edad"] == "3"
