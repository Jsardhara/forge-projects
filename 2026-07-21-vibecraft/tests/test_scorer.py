"""Tests for the craftsmanship scorer."""

import pytest

from vibecraft.models import FindingCode, Severity
from vibecraft.scorer import score_craftsmanship
from fixtures import (
    BARE_EXCEPT_CODE,
    CONSISTENT_SNAKE,
    DEEP_NESTING_CODE,
    HARDCODE_URL_CODE,
    INCONSISTENT_NAMING,
    LONG_FUNCTION_CODE,
    MAGIC_NUMBER_CODE,
    MAGIC_STRING_CODE,
    MISSING_DOCSTRING_CODE,
    VIBE_CODED_PYTHON,
)


class TestScoreGrades:
    def test_clean_code_gets_A(self):
        clean = '''
def get_user_id():
    """Return the user ID."""
    return 1
'''
        report = score_craftsmanship(clean, "clean.py")
        assert report.grade == "A"

    def test_empty_source_gets_A(self):
        report = score_craftsmanship("", "empty.py")
        assert report.grade == "A"
        assert report.score == 100.0

    def test_vibe_coded_gets_low_score(self):
        report = score_craftsmanship(VIBE_CODED_PYTHON, "vibe.py")
        assert report.score < 60
        assert report.grade in ("D", "F")


class TestSubscores:
    def test_doc_coverage_calculated(self):
        report = score_craftsmanship(CONSISTENT_SNAKE, "test.py")
        assert report.doc_coverage == 0.0  # snake_code has no docstrings

    def test_error_handling_penalty(self):
        report = score_craftsmanship(BARE_EXCEPT_CODE, "test.py")
        assert report.error_handling_score < 1.0

    def test_deep_nesting_penalty(self):
        report = score_craftsmanship(DEEP_NESTING_CODE, "test.py")
        assert report.complexity_score < 1.0

    def test_magic_string_penalty(self):
        report = score_craftsmanship(MAGIC_STRING_CODE, "test.py")
        assert report.score < 100.0


class TestFindings:
    def test_findings_attached_to_report(self):
        report = score_craftsmanship(VIBE_CODED_PYTHON, "vibe.py")
        assert report.finding_count >= 3

    def test_severity_levels(self):
        findings = [f.severity for f in score_craftsmanship(BARE_EXCEPT_CODE, "test.py").findings]
        assert Severity.WARNING in findings or Severity.CRITICAL in findings


class TestBanding:
    def test_banding_good(self):
        report = score_craftsmanship("def f(): return 1", "test.py")
        assert report.band() == "good"

    def test_banding_poor(self):
        report = score_craftsmanship(VIBE_CODED_PYTHON, "vibe.py")
        assert report.band() in ("poor", "fair")

    def test_to_dict_works(self):
        report = score_craftsmanship(HARDCODE_URL_CODE, "test.py")
        d = report.to_dict()
        assert "score" in d
        assert "grade" in d
        assert "findings" in d
        assert "band" in d


class TestLineCount:
    def test_total_lines_counted(self):
        report = score_craftsmanship(BARE_EXCEPT_CODE, "test.py")
        assert report.total_lines > 0
