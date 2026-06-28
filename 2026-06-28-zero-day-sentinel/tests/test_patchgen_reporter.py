"""Tests for ZeroDaySentinel patch generator and reporter."""

from datetime import datetime, timezone
from zerosentinel.models import (
    DetectionResult,
    PatchSuggestion,
    Severity,
    VulnerabilityFingerprint,
)
from zerosentinel.patchgen import PatchGenerator
from zerosentinel.reporter import ReportGenerator


def _make_fp(
    product: str = "linux",
    vuln_type: str = "rce",
    severity: Severity = Severity.CRITICAL,
    cve_id: str | None = None,
    versions: tuple = (),
) -> VulnerabilityFingerprint:
    return VulnerabilityFingerprint(
        cve_id=cve_id,
        affected_product=product,
        affected_versions=versions,
        vulnerability_type=vuln_type,
        severity=severity,
        summary=f"{vuln_type} in {product}",
    )


class TestPatchGenerator:
    def setup_method(self):
        self.gen = PatchGenerator()

    def test_generates_suggestion(self):
        fp = _make_fp()
        suggestion = self.gen.generate(fp)
        assert suggestion.fingerprint is fp
        assert suggestion.confidence > 0.0
        assert suggestion.suggested_fix != ""
        assert suggestion.patch_type in ("version_pin", "config_change", "code_fix", "workaround")

    def test_confidence_boost_with_cve(self):
        fp_no_cve = _make_fp(cve_id=None)
        fp_with_cve = _make_fp(cve_id="CVE-2026-0001")
        s1 = self.gen.generate(fp_no_cve)
        s2 = self.gen.generate(fp_with_cve)
        assert s2.confidence >= s1.confidence

    def test_confidence_boost_with_versions(self):
        fp_no_ver = _make_fp(versions=())
        fp_with_ver = _make_fp(versions=("6.8.0",))
        s1 = self.gen.generate(fp_no_ver)
        s2 = self.gen.generate(fp_with_ver)
        assert s2.confidence >= s1.confidence

    def test_critical_rce_is_high_effort(self):
        fp = _make_fp(severity=Severity.CRITICAL, vuln_type="rce")
        suggestion = self.gen.generate(fp)
        assert suggestion.estimated_effort == "high"

    def test_medium_xss_is_low_effort(self):
        fp = _make_fp(severity=Severity.MEDIUM, vuln_type="xss")
        suggestion = self.gen.generate(fp)
        assert suggestion.estimated_effort == "low"

    def test_batch_generation(self):
        fps = [
            _make_fp(product="linux", vuln_type="rce", severity=Severity.CRITICAL),
            _make_fp(product="nginx", vuln_type="xss", severity=Severity.MEDIUM),
        ]
        suggestions = self.gen.generate_batch(fps)
        assert len(suggestions) == 2

    def test_unknown_type_gets_workaround(self):
        fp = _make_fp(vuln_type="unknown")
        suggestion = self.gen.generate(fp)
        assert suggestion.patch_type == "workaround"

    def test_kernel_type_is_version_pin(self):
        fp = _make_fp(vuln_type="kernel")
        suggestion = self.gen.generate(fp)
        assert suggestion.patch_type == "version_pin"


class TestReportGenerator:
    def setup_method(self):
        self.reporter = ReportGenerator()

    def test_text_report_empty(self):
        result = DetectionResult(
            scan_timestamp=datetime.now(timezone.utc),
            repos_scanned=5,
            matches=(),
            patch_suggestions=(),
            scan_duration_seconds=0.1,
        )
        report = self.reporter.generate_text_report(result)
        assert "ZeroDaySentinel" in report
        assert "Repos Scanned:    5" in report
        assert "No 0-day vulnerabilities detected" in report

    def test_text_report_with_matches(self):
        fp = _make_fp()
        suggestion = PatchSuggestion(
            fingerprint=fp,
            confidence=0.95,
            suggested_fix="Update linux kernel immediately",
            patch_type="version_pin",
        )
        result = DetectionResult(
            scan_timestamp=datetime.now(timezone.utc),
            repos_scanned=3,
            matches=(fp,),
            patch_suggestions=(suggestion,),
            scan_duration_seconds=0.5,
        )
        report = self.reporter.generate_text_report(result)
        assert "[CRITICAL]" in report
        assert "linux" in report
        assert "PATCH SUGGESTIONS" in report

    def test_json_report_empty(self):
        result = DetectionResult(
            scan_timestamp=datetime.now(timezone.utc),
            repos_scanned=0,
            matches=(),
            patch_suggestions=(),
            scan_duration_seconds=0.0,
        )
        report = self.reporter.generate_json_report(result)
        import json
        data = json.loads(report)
        assert data["total_matches"] == 0
        assert data["critical_count"] == 0

    def test_json_report_with_matches(self):
        fp = _make_fp(cve_id="CVE-2026-0001")
        result = DetectionResult(
            scan_timestamp=datetime.now(timezone.utc),
            repos_scanned=3,
            matches=(fp,),
            patch_suggestions=(),
            scan_duration_seconds=0.1,
        )
        report = self.reporter.generate_json_report(result)
        import json
        data = json.loads(report)
        assert data["total_matches"] == 1
        assert data["critical_count"] == 1
        assert data["matches"][0]["cve_id"] == "CVE-2026-0001"

    def test_severity_badge(self):
        assert "CRITICAL" in ReportGenerator._severity_badge(Severity.CRITICAL)
        assert "HIGH" in ReportGenerator._severity_badge(Severity.HIGH)
        assert "MEDIUM" in ReportGenerator._severity_badge(Severity.MEDIUM)
