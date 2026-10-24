"""Tests for plugattest.models — severity ordering and report aggregation."""

import unittest

from plugattest.models import (
    Finding,
    Report,
    Severity,
    SEVERITY_RANK,
    worst_severity,
    score_findings,
)


class TestSeverityOrdering(unittest.TestCase):
    def test_rank_is_integer_and_ordered(self):
        self.assertLess(SEVERITY_RANK[Severity.PASS], SEVERITY_RANK[Severity.INFO])
        self.assertLess(SEVERITY_RANK[Severity.INFO], SEVERITY_RANK[Severity.WARN])
        self.assertLess(SEVERITY_RANK[Severity.WARN], SEVERITY_RANK[Severity.FLAG])

    def test_worst_severity_is_not_lexicographic(self):
        # Lexicographic max over "PASS"/"FLAG" picks "PASS" ('P' > 'F'). Guard against it.
        self.assertIs(worst_severity([Severity.PASS, Severity.FLAG]), Severity.FLAG)
        self.assertIs(worst_severity([Severity.FLAG, Severity.PASS]), Severity.FLAG)

    def test_worst_severity_empty_is_pass(self):
        self.assertIs(worst_severity([]), Severity.PASS)


class TestScore(unittest.TestCase):
    def test_no_findings_scores_zero(self):
        self.assertEqual(score_findings([]), 0)

    def test_score_is_capped_at_100(self):
        findings = [Finding("PA-001", Severity.FLAG, "x", "undeclared") for _ in range(10)]
        self.assertEqual(score_findings(findings), 100)

    def test_info_does_not_raise_score(self):
        findings = [Finding("PA-002", Severity.INFO, "x", "declared-unused")]
        self.assertEqual(score_findings(findings), 0)


class TestReport(unittest.TestCase):
    def test_clean_report_is_pass(self):
        report = Report(package="p", declared=(), detected=(), findings=())
        self.assertIs(report.verdict, Severity.PASS)
        self.assertEqual(report.score, 0)

    def test_verdict_is_worst_single_finding_not_sum(self):
        findings = [
            Finding("PA-003", Severity.WARN, "a.py:1", "no declaration"),
            Finding("PA-002", Severity.INFO, "b.py:2", "unused"),
        ]
        report = Report(package="p", declared=(), detected=(), findings=tuple(findings))
        self.assertIs(report.verdict, Severity.WARN)
        self.assertGreater(report.score, 0)

    def test_to_dict_is_json_ready(self):
        report = Report(package="p", declared=("network",), detected=(), findings=())
        data = report.to_dict()
        self.assertEqual(data["package"], "p")
        self.assertEqual(data["verdict"], "PASS")
        self.assertEqual(data["declared"], ["network"])
        self.assertIsInstance(data["findings"], list)


if __name__ == "__main__":
    unittest.main()
