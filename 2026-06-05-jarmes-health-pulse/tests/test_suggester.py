"""Tests for healthpulse.suggester module."""

from healthpulse.suggester import get_suggestion, KNOWN_FIXES


class TestGetSuggestion:
    def test_known_pattern(self):
        suggestion = get_suggestion("string_pattern_mismatch: input_value='completed'")
        assert suggestion is not None
        assert "status" in suggestion.lower() or "task" in suggestion.lower()

    def test_validation_error(self):
        suggestion = get_suggestion("pydantic_core._pydantic_core.ValidationError: 1 validation error")
        assert suggestion is not None
        assert "Pydantic" in suggestion or "validation" in suggestion.lower()

    def test_module_not_found(self):
        suggestion = get_suggestion("ModuleNotFoundError: No module named 'foo'")
        assert suggestion is not None
        assert "module" in suggestion.lower() or "install" in suggestion.lower()

    def test_unknown_pattern(self):
        suggestion = get_suggestion("Some completely unknown error XYZ-123")
        assert suggestion is None

    def test_known_fixes_not_empty(self):
        assert len(KNOWN_FIXES) > 0
