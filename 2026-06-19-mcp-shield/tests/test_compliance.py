"""Tests for mcp_shield.compliance module."""

import pytest

from mcp_shield.audit import AuditLogger
from mcp_shield.compliance import (
    ComplianceReport,
    ComplianceStandard,
    ComplianceFinding,
    generate_report,
)


class TestComplianceFinding:
    def test_creation(self):
        f = ComplianceFinding(
            standard="soc2",
            control="AC-1",
            status="pass",
            description="All access controlled",
        )
        assert f.status == "pass"
        assert f.evidence == ""


class TestComplianceReport:
    def test_is_compliant_all_pass(self):
        report = ComplianceReport(
            generated_at="2026-06-19T00:00:00+00:00",
            standard=ComplianceStandard.SOC2,
            agent_id="a1",
            period_start="2026-06-01",
            period_end="2026-06-19",
            findings=[
                ComplianceFinding("soc2", "AC-1", "pass", "ok"),
                ComplianceFinding("soc2", "AU-2", "pass", "ok"),
            ],
        )
        assert report.is_compliant() is True

    def test_is_compliant_with_fail(self):
        report = ComplianceReport(
            generated_at="2026-06-19T00:00:00+00:00",
            standard=ComplianceStandard.SOC2,
            agent_id="a1",
            period_start="2026-06-01",
            period_end="2026-06-19",
            findings=[
                ComplianceFinding("soc2", "AC-1", "pass", "ok"),
                ComplianceFinding("soc2", "AU-2", "fail", "missing logs"),
            ],
        )
        assert report.is_compliant() is False

    def test_is_compliant_warnings_only(self):
        report = ComplianceReport(
            generated_at="2026-06-19T00:00:00+00:00",
            standard=ComplianceStandard.SOC2,
            agent_id="a1",
            period_start="2026-06-01",
            period_end="2026-06-19",
            findings=[
                ComplianceFinding("soc2", "AC-1", "warning", "check"),
            ],
        )
        assert report.is_compliant() is True

    def test_summary(self):
        report = ComplianceReport(
            generated_at="2026-06-19T00:00:00+00:00",
            standard=ComplianceStandard.SOC2,
            agent_id="a1",
            period_start="2026-06-01",
            period_end="2026-06-19",
            total_events=10,
            critical_events=1,
            denied_events=2,
            avg_risk=0.3,
            findings=[
                ComplianceFinding("soc2", "AC-1", "pass", "ok"),
                ComplianceFinding("soc2", "AU-2", "warning", "check"),
            ],
            recommendations=["Review warnings"],
        )
        s = report.summary()
        assert s["standard"] == "soc2"
        assert s["total_events"] == 10
        assert s["compliant"] is True
        assert s["findings"]["pass"] == 1
        assert s["findings"]["warning"] == 1
        assert s["recommendations"] == 1

    def test_to_json(self):
        report = ComplianceReport(
            generated_at="2026-06-19T00:00:00+00:00",
            standard=ComplianceStandard.SOC2,
            agent_id="a1",
            period_start="2026-06-01",
            period_end="2026-06-19",
        )
        raw = report.to_json()
        assert "soc2" in raw
        assert "a1" in raw


class TestGenerateReport:
    def _make_audit(self):
        audit = AuditLogger()
        # Normal activity
        for _ in range(5):
            audit.log(
                agent_id="agent-001", tool_name="read_file", server_id="dev",
                arguments={"path": "/x"}, action="tool_call", decision="allow", risk_score=0.1,
            )
        # Suspicious activity
        audit.log(
            agent_id="agent-001", tool_name="exec", server_id="dev",
            arguments={"command": "sudo rm -rf /"}, action="tool_call", decision="deny", risk_score=0.95,
        )
        # Another agent
        audit.log(
            agent_id="agent-002", tool_name="read_file", server_id="dev",
            arguments={}, action="tool_call", decision="allow", risk_score=0.1,
        )
        return audit

    def test_soc2_report(self):
        audit = self._make_audit()
        report = generate_report(audit, "agent-001", ComplianceStandard.SOC2)
        assert report.standard == ComplianceStandard.SOC2
        assert report.agent_id == "agent-001"
        assert report.total_events == 6  # 5 reads + 1 exec
        assert report.denied_events == 1
        assert report.critical_events == 1
        assert len(report.findings) > 0
        assert len(report.recommendations) > 0

    def test_gdpr_report(self):
        audit = self._make_audit()
        report = generate_report(audit, "agent-001", ComplianceStandard.GDPR)
        assert report.standard == ComplianceStandard.GDPR
        assert report.total_events == 6

    def test_empty_audit(self):
        audit = AuditLogger()
        report = generate_report(audit, "agent-001", ComplianceStandard.SOC2)
        assert report.total_events == 0
        assert report.is_compliant() is False  # no events = fail on AU-2

    def test_avg_risk_calculation(self):
        audit = self._make_audit()
        report = generate_report(audit, "agent-001", ComplianceStandard.SOC2)
        # 5 events at 0.1 + 1 event at 0.95 = 1.45 / 6 ≈ 0.242
        assert report.avg_risk == pytest.approx(0.242, abs=0.01)

    def test_recommendations_generated(self):
        audit = self._make_audit()
        report = generate_report(audit, "agent-001", ComplianceStandard.SOC2)
        # Should have at least one recommendation about the denied exec
        assert any("high-risk" in r.lower() or "critical" in r.lower() or "urgent" in r.lower() or "warning" in r.lower() for r in report.recommendations)
