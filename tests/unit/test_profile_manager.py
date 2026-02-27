# tests/unit/test_profile_manager.py
import pytest

from src.core.profile_manager import UserProfileManager
from src.core.profile_seeder import ensure_profile_complete, get_default_profile


@pytest.fixture
def manager():
    return UserProfileManager()


class TestProfileManagerDefaults:
    def test_default_profile_has_new_sections(self, manager):
        """Default profile must include support_preferences, coping, memory, clinical."""
        profile = get_default_profile()
        assert "support_preferences" in profile
        assert "coping_mechanisms" in profile
        assert "memory_settings" in profile
        assert "clinical_safety" in profile
        assert profile["memory_settings"]["consent_given"] is True
        assert profile["memory_settings"]["ephemeral_mode"] is False

    def test_default_profile_version_is_1_2(self, manager):
        profile = get_default_profile()
        assert profile["metadata"]["version"] == "1.2.0"


class TestProfileMigration:
    def test_ensure_complete_fills_missing_sections(self, manager):
        """Old profiles missing new sections get defaults filled in."""
        old = {
            "identity": {"name": "Jhonn", "style": "Casual"},
            "personality_adaptation": {"humor_tolerance": 0.9},
            "metadata": {"version": "1.1.0"},
        }
        complete = ensure_profile_complete(old)
        assert complete["identity"]["name"] == "Jhonn"  # preserved
        assert complete["support_preferences"]["response_style"] == "balanced"  # filled
        assert complete["clinical_safety"]["disclaimer_shown"] is False  # filled
        assert complete["metadata"]["version"] == "1.2.0"  # bumped

    def test_ensure_complete_preserves_existing_data(self, manager):
        """Existing data must not be overwritten by defaults."""
        old = {
            "identity": {"name": "Jhonn", "style": "Poético"},
            "personality_adaptation": {"humor_tolerance": 0.9, "formality_level": 0.1},
            "psychological_state": {
                "current_phase": "Growth",
                "key_metaphors": ["río"],
            },
            "values_and_goals": {"core_values": ["honestidad"]},
            "metadata": {"version": "1.1.0"},
        }
        complete = ensure_profile_complete(old)
        assert complete["identity"]["style"] == "Poético"
        assert complete["personality_adaptation"]["humor_tolerance"] == 0.9
        assert complete["psychological_state"]["key_metaphors"] == ["río"]
        assert complete["values_and_goals"]["core_values"] == ["honestidad"]
