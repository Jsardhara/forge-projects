"""Tests for the Gateway facade."""

from __future__ import annotations

from edugate.gateway import Gateway
from edugate.policy import AccessRequest, Student


class TestGateway:
    def setup_method(self):
        self.gateway = Gateway(school_name="Test Skole")
        self.gateway.policy.load_norway_defaults()

    def test_check_access_denies_elementary(self):
        req = AccessRequest(
            student=Student("S1", "Ada", grade=5, age=10),
            tool_name="ChatGPT",
            timestamp="2026-06-20T10:00:00+00:00",
        )
        result = self.gateway.check_access(req)
        assert result.decision.value == "deny"

    def test_check_access_logs_event(self):
        req = AccessRequest(
            student=Student("S1", "Ada", grade=5, age=10),
            tool_name="ChatGPT",
            timestamp="2026-06-20T10:00:00+00:00",
        )
        self.gateway.check_access(req)
        assert len(self.gateway.audit.events) == 1
        assert self.gateway.audit.events[0].student_id == "S1"

    def test_multiple_checks_log_multiple_events(self):
        students = [
            Student("S1", "Ada", grade=5, age=10),
            Student("S2", "Bjorn", grade=9, age=15),
            Student("S3", "Clara", grade=12, age=18),
        ]
        for s in students:
            req = AccessRequest(
                student=s, tool_name="ChatGPT",
                timestamp="2026-06-20T10:00:00+00:00",
                teacher_present=(s.grade >= 8),
            )
            self.gateway.check_access(req)

        assert len(self.gateway.audit.events) == 3
        summary = self.gateway.audit.summary()
        assert summary["total_events"] == 3
        assert summary["unique_students"] == 3

    def test_compliance_report_from_audit_data(self):
        # Generate some activity
        students = [
            Student("S1", "Ada", grade=5, age=10),
            Student("S2", "Bjorn", grade=9, age=15),
            Student("S3", "Clara", grade=12, age=18),
        ]
        for s in students:
            req = AccessRequest(
                student=s, tool_name="ChatGPT",
                timestamp="2026-06-20T10:00:00+00:00",
                teacher_present=(s.grade >= 8),
            )
            self.gateway.check_access(req)

        report = self.gateway.generate_compliance_report()
        assert report.school_name == "Test Skole"
        assert report.framework == "Norway-2026"
        assert len(report.findings) > 0

    def test_full_workflow(self):
        """End-to-end: elementary denied, lower secondary supervised, upper secondary allowed."""
        ts = "2026-06-20T10:00:00+00:00"

        # Elementary → denied
        elem_req = AccessRequest(
            student=Student("S1", "Ada", grade=5, age=10),
            tool_name="ChatGPT", timestamp=ts,
        )
        elem_result = self.gateway.check_access(elem_req)
        assert elem_result.decision.value == "deny"

        # Lower secondary without teacher → denied
        low_req = AccessRequest(
            student=Student("S2", "Bjorn", grade=9, age=15),
            tool_name="Claude", timestamp=ts, teacher_present=False,
        )
        low_result = self.gateway.check_access(low_req)
        assert low_result.decision.value == "deny"

        # Lower secondary with teacher → allowed
        low_sup_req = AccessRequest(
            student=Student("S2", "Bjorn", grade=9, age=15),
            tool_name="Claude", timestamp=ts, teacher_present=True,
        )
        low_sup_result = self.gateway.check_access(low_sup_req)
        assert low_sup_result.decision.value == "allow"

        # Upper secondary → allowed
        up_req = AccessRequest(
            student=Student("S3", "Clara", grade=12, age=18),
            tool_name="Gemini", timestamp=ts,
        )
        up_result = self.gateway.check_access(up_req)
        assert up_result.decision.value == "allow"

        # Verify audit trail
        assert len(self.gateway.audit.events) == 4

        # Verify compliance report
        report = self.gateway.generate_compliance_report()
        assert "COMPLIANT" in report.summary.upper() or "NON-COMPLIANT" in report.summary.upper()
