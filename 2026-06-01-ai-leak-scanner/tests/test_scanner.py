"""Tests for AI Leak Scanner."""

import pytest

from ai_leak_scanner.vulndb import (
    VULNERABILITIES,
    Severity,
    AttackVector,
    get_vulnerability,
    get_by_vendor,
    get_by_severity,
    get_unpatched,
    get_attack_vectors,
)
from ai_leak_scanner.scanner import (
    scan_extensions,
    scan_all,
    get_risk_level,
    _calculate_risk_score,
    ScanFinding,
)


# ── Vulnerability Database Tests ─────────────────────────────────────────────

class TestVulnDB:
    def test_vulndb_not_empty(self):
        assert len(VULNERABILITIES) > 0

    def test_vulndb_has_critical(self):
        critical = [v for v in VULNERABILITIES if v.severity == Severity.CRITICAL]
        assert len(critical) > 0

    def test_vulndb_has_openai(self):
        openai = get_by_vendor("OpenAI")
        assert len(openai) > 0

    def test_vulndb_has_anthropic(self):
        anthropic = get_by_vendor("Anthropic")
        assert len(anthropic) > 0

    def test_get_vulnerability_found(self):
        v = get_vulnerability("VULN-001")
        assert v is not None
        assert v.vendor == "OpenAI"

    def test_get_vulnerability_not_found(self):
        v = get_vulnerability("VULN-999")
        assert v is None

    def test_get_by_severity_critical(self):
        critical = get_by_severity(Severity.CRITICAL)
        assert all(v.severity == Severity.CRITICAL for v in critical)

    def test_get_by_severity_high_includes_critical(self):
        high = get_by_severity(Severity.HIGH)
        critical = get_by_severity(Severity.CRITICAL)
        assert len(high) >= len(critical)

    def test_get_unpatched(self):
        unpatched = get_unpatched()
        assert len(unpatched) > 0
        assert all(not v.patched for v in unpatched)

    def test_chatgpt_sheets_patched(self):
        v = get_vulnerability("VULN-001")
        assert v is not None
        assert v.patched is True

    def test_attack_vectors_exist(self):
        vectors = get_attack_vectors()
        assert len(vectors) > 0
        assert AttackVector.INDIRECT_PROMPT_INJECTION in vectors
        assert AttackVector.DATA_EXFILTRATION in vectors

    def test_all_vulns_have_ids(self):
        ids = [v.vid for v in VULNERABILITIES]
        assert len(ids) == len(set(ids)), "Duplicate vulnerability IDs found"

    def test_all_vulns_have_references(self):
        for v in VULNERABILITIES:
            assert len(v.references) > 0, f"{v.vid} has no references"

    def test_all_vulns_have_mitigation(self):
        for v in VULNERABILITIES:
            assert v.mitigation, f"{v.vid} has no mitigation"


# ── Scanner Engine Tests ─────────────────────────────────────────────────────

class TestScanner:
    def test_scan_detects_chatgpt_sheets(self):
        report = scan_extensions(["ChatGPT for Google Sheets"])
        detected = [f for f in report.findings if f.detected]
        assert len(detected) > 0
        vuln_ids = [f.vulnerability.vid for f in detected]
        assert "VULN-001" in vuln_ids

    def test_scan_detects_claude_cowork(self):
        report = scan_extensions(["Claude Cowork"])
        detected = [f for f in report.findings if f.detected]
        assert len(detected) > 0
        vuln_ids = [f.vulnerability.vid for f in detected]
        assert "VULN-002" in vuln_ids

    def test_scan_no_false_positives_for_unknown(self):
        report = scan_extensions(["Totally Unknown AI Tool XYZ"])
        detected = [f for f in report.findings if f.detected]
        assert len(detected) == 0

    def test_scan_risk_score_zero_for_clean(self):
        report = scan_extensions(["Unknown Safe Tool"])
        assert report.risk_score == 0.0

    def test_scan_risk_score_nonzero_for_vuln(self):
        report = scan_extensions(["ChatGPT for Google Sheets"])
        assert report.risk_score > 0.0

    def test_scan_all_detects_everything(self):
        report = scan_all()
        detected = [f for f in report.findings if f.detected]
        assert len(detected) == len(VULNERABILITIES)

    def test_scan_report_has_summary(self):
        report = scan_extensions(["ChatGPT for Google Sheets"])
        assert report.summary
        assert len(report.summary) > 0

    def test_scan_report_counts(self):
        report = scan_extensions(["ChatGPT for Google Sheets", "Claude Cowork"])
        assert report.total_detected >= 2

    def test_scan_unpatched_count(self):
        report = scan_extensions(["Claude Cowork"])
        assert report.unpatched_detected >= 1

    def test_risk_level_critical(self):
        assert get_risk_level(80.0) == "CRITICAL"

    def test_risk_level_high(self):
        assert get_risk_level(60.0) == "HIGH"

    def test_risk_level_medium(self):
        assert get_risk_level(30.0) == "MEDIUM"

    def test_risk_level_low(self):
        assert get_risk_level(15.0) == "LOW"

    def test_risk_level_minimal(self):
        assert get_risk_level(5.0) == "MINIMAL"

    def test_risk_score_capped_at_100(self):
        findings = [
            ScanFinding(
                vulnerability=VULNERABILITIES[0],
                detected=True,
                confidence=1.0,
            )
            for _ in range(100)
        ]
        score = _calculate_risk_score(findings)
        assert score <= 100.0

    def test_scan_multiple_extensions(self):
        report = scan_extensions([
            "ChatGPT for Google Sheets",
            "Claude Cowork",
            "Notion AI",
            "Slack AI",
        ])
        assert report.total_detected >= 4

    def test_scan_case_insensitive(self):
        report = scan_extensions(["chatgpt for google sheets"])
        detected = [f for f in report.findings if f.detected]
        assert len(detected) > 0


# ── Database Statistics Tests ────────────────────────────────────────────────

class TestStats:
    def test_total_count(self):
        assert len(VULNERABILITIES) >= 15

    def test_vendors_list(self):
        vendors = set(v.vendor for v in VULNERABILITIES)
        assert "OpenAI" in vendors
        assert "Anthropic" in vendors

    def test_severity_distribution(self):
        critical = len([v for v in VULNERABILITIES if v.severity == Severity.CRITICAL])
        high = len([v for v in VULNERABILITIES if v.severity == Severity.HIGH])
        medium = len([v for v in VULNERABILITIES if v.severity == Severity.MEDIUM])
        assert critical > 0
        assert high > 0
        assert medium > 0

    def test_attack_vector_coverage(self):
        vectors = get_attack_vectors()
        assert AttackVector.INDIRECT_PROMPT_INJECTION in vectors
        assert AttackVector.DATA_EXFILTRATION in vectors
        assert AttackVector.PHISHING_OVERLAY in vectors
