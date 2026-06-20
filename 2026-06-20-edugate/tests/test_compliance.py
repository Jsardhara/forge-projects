"""Tests for compliance reporting."""

from __future__ import annotations

from edugate.compliance import generate_norway_compliance


class TestNorwayCompliance:
    def test_fully_compliant(self):
        report = generate_norway_compliance(
            school_name="Test School",
            total_events=10,
            elementary_denied=5,
            elementary_total=5,
            lower_secondary_supervised=3,
            lower_secondary_total=3,
            has_audit_trail=True,
            has_policy_configured=True,
        )
        assert report.framework == "Norway-2026"
        assert report.school_name == "Test School"
        assert "FULLY COMPLIANT" in report.summary
        assert all(f.status == "pass" for f in report.findings)

    def test_non_compliant_elementary(self):
        report = generate_norway_compliance(
            school_name="Test School",
            total_events=10,
            elementary_denied=2,
            elementary_total=5,
            lower_secondary_supervised=3,
            lower_secondary_total=3,
            has_audit_trail=True,
            has_policy_configured=True,
        )
        assert "NON-COMPLIANT" in report.summary
        elem_findings = [f for f in report.findings if f.control_id == "ELEM-001"]
        assert len(elem_findings) == 1
        assert elem_findings[0].status == "fail"

    def test_no_audit_trail(self):
        report = generate_norway_compliance(
            school_name="Test School",
            total_events=0,
            elementary_denied=0,
            elementary_total=0,
            lower_secondary_supervised=0,
            lower_secondary_total=0,
            has_audit_trail=False,
            has_policy_configured=True,
        )
        audit_findings = [f for f in report.findings if f.control_id == "AUDIT-001"]
        assert len(audit_findings) == 1
        assert audit_findings[0].status == "fail"

    def test_no_policy_configured(self):
        report = generate_norway_compliance(
            school_name="Test School",
            total_events=5,
            elementary_denied=0,
            elementary_total=0,
            lower_secondary_supervised=0,
            lower_secondary_total=0,
            has_audit_trail=True,
            has_policy_configured=False,
        )
        policy_findings = [f for f in report.findings if f.control_id == "POL-001"]
        assert len(policy_findings) == 1
        assert policy_findings[0].status == "fail"

    def test_warning_for_partial_supervision(self):
        report = generate_norway_compliance(
            school_name="Test School",
            total_events=10,
            elementary_denied=0,
            elementary_total=0,
            lower_secondary_supervised=5,
            lower_secondary_total=10,
            has_audit_trail=True,
            has_policy_configured=True,
        )
        # 50% supervision rate is below 90% threshold → warning
        lowsec_findings = [f for f in report.findings if f.control_id == "LOWSEC-001"]
        assert len(lowsec_findings) == 1
        assert lowsec_findings[0].status == "warning"

    def test_zero_events_passes_elementary(self):
        report = generate_norway_compliance(
            school_name="Test School",
            total_events=0,
            elementary_denied=0,
            elementary_total=0,
            lower_secondary_supervised=0,
            lower_secondary_total=0,
            has_audit_trail=True,
            has_policy_configured=True,
        )
        elem_findings = [f for f in report.findings if f.control_id == "ELEM-001"]
        assert len(elem_findings) == 1
        assert elem_findings[0].status == "pass"

    def test_report_has_id_and_timestamp(self):
        report = generate_norway_compliance(
            school_name="Test School",
            total_events=0,
            elementary_denied=0,
            elementary_total=0,
            lower_secondary_supervised=0,
            lower_secondary_total=0,
            has_audit_trail=True,
            has_policy_configured=True,
        )
        assert report.report_id.startswith("NO-WAY-")
        assert report.generated_at is not None
