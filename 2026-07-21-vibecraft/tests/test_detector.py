"""Tests for the pattern detector."""

import pytest

from vibecraft.detector import detect_patterns
from vibecraft.models import FindingCode, Severity
from fixtures import (
    BARE_EXCEPT_CODE,
    DEEP_NESTING_CODE,
    EXCEPT_PASS_CODE,
    HARDCODE_URL_CODE,
    INCONSISTENT_NAMING,
    LONG_FUNCTION_CODE,
    MAGIC_NUMBER_CODE,
    MAGIC_STRING_CODE,
    MISSING_DOCSTRING_CODE,
    VIBE_CODED_PYTHON,
)


class TestBareExcept:
    def test_bare_except_detected(self):
        findings = detect_patterns(BARE_EXCEPT_CODE)
        codes = [f.code for f in findings]
        assert FindingCode.BARE_EXCEPT in codes

    def test_except_pass_detected(self):
        findings = detect_patterns(EXCEPT_PASS_CODE)
        codes = [f.code for f in findings]
        assert FindingCode.EXCEPT_PASS in codes

    def test_vibe_coded_has_bare_except(self):
        findings = detect_patterns(VIBE_CODED_PYTHON)
        codes = [f.code for f in findings]
        assert FindingCode.BARE_EXCEPT in codes

    def test_vibe_coded_has_print(self):
        findings = detect_patterns(VIBE_CODED_PYTHON)
        codes = [f.code for f in findings]
        assert FindingCode.PRINT_IN_CODE in codes

    def test_vibe_coded_has_incomplete_todo(self):
        findings = detect_patterns(VIBE_CODED_PYTHON)
        codes = [f.code for f in findings]
        assert FindingCode.INCOMPLETE_TODO in codes


class TestDeepNesting:
    def test_deep_nesting_detected(self):
        findings = detect_patterns(DEEP_NESTING_CODE)
        codes = [f.code for f in findings]
        assert FindingCode.DEEP_NESTING in codes


class TestLongFunction:
    def test_long_function_detected(self):
        findings = detect_patterns(LONG_FUNCTION_CODE)
        codes = [f.code for f in findings]
        assert FindingCode.LONG_FUNCTION in codes


class TestMissingDocstring:
    def test_missing_docstring_on_function(self):
        findings = detect_patterns(MISSING_DOCSTRING_CODE)
        codes = [f.code for f in findings]
        assert FindingCode.MISSING_DOCSTRING in codes

    def test_missing_docstring_on_class(self):
        findings = detect_patterns(MISSING_DOCSTRING_CODE)
        codes = [f.code for f in findings]
        assert FindingCode.MISSING_DOCSTRING in codes


class TestMagicValues:
    def test_magic_string_detected(self):
        findings = detect_patterns(MAGIC_STRING_CODE)
        codes = [f.code for f in findings]
        assert FindingCode.MAGIC_STRING in codes

    def test_magic_number_detected(self):
        findings = detect_patterns(MAGIC_NUMBER_CODE)
        codes = [f.code for f in findings]
        assert FindingCode.MAGIC_NUMBER in codes


class TestHardcodedUrl:
    def test_hardcoded_url_detected(self):
        findings = detect_patterns(HARDCODE_URL_CODE)
        codes = [f.code for f in findings]
        assert FindingCode.HARDCODE_URL in codes


class TestNaming:
    def test_inconsistent_naming_detected(self):
        findings = detect_patterns(INCONSISTENT_NAMING)
        codes = [f.code for f in findings]
        assert FindingCode.INCONSISTENT_NAMING in codes


class TestEmptySource:
    def test_empty_source_returns_empty_list(self):
        findings = detect_patterns("")
        assert findings == []

    def test_syntax_error_returns_empty_list(self):
        findings = detect_patterns("def f(\n")
        assert findings == []
