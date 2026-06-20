"""Tests for the policy engine."""

from __future__ import annotations

from edugate.policy import (
    AccessDecision,
    AccessPolicy,
    AccessRequest,
    GradeBand,
    PolicyEngine,
    Student,
)


class TestStudent:
    def test_elementary_band(self):
        s = Student("S1", "Ada", grade=5, age=10)
        assert s.grade_band == GradeBand.ELEMENTARY

    def test_lower_secondary_band(self):
        s = Student("S2", "Bjorn", grade=9, age=15)
        assert s.grade_band == GradeBand.LOWER_SECONDARY

    def test_upper_secondary_band(self):
        s = Student("S3", "Clara", grade=12, age=18)
        assert s.grade_band == GradeBand.UPPER_SECONDARY

    def test_grade_boundaries(self):
        assert Student("S", "A", grade=7, age=13).grade_band == GradeBand.ELEMENTARY
        assert Student("S", "B", grade=8, age=14).grade_band == GradeBand.LOWER_SECONDARY
        assert Student("S", "C", grade=10, age=16).grade_band == GradeBand.LOWER_SECONDARY
        assert Student("S", "D", grade=11, age=17).grade_band == GradeBand.UPPER_SECONDARY


class TestPolicyEngineDefaults:
    def setup_method(self):
        self.engine = PolicyEngine()
        self.engine.load_norway_defaults()

    def test_elementary_denied(self):
        req = AccessRequest(
            student=Student("S1", "Ada", grade=5, age=10),
            tool_name="ChatGPT",
            timestamp="2026-06-20T10:00:00+00:00",
            teacher_present=False,
        )
        result = self.engine.check(req)
        assert result.decision == AccessDecision.DENY

    def test_elementary_denied_even_with_teacher(self):
        """Elementary students should be denied even with teacher present."""
        req = AccessRequest(
            student=Student("S1", "Ada", grade=5, age=10),
            tool_name="ChatGPT",
            timestamp="2026-06-20T10:00:00+00:00",
            teacher_present=True,
        )
        result = self.engine.check(req)
        assert result.decision == AccessDecision.DENY

    def test_lower_secondary_requires_supervision(self):
        req = AccessRequest(
            student=Student("S2", "Bjorn", grade=9, age=15),
            tool_name="Claude",
            timestamp="2026-06-20T10:00:00+00:00",
            teacher_present=False,
        )
        result = self.engine.check(req)
        assert result.decision == AccessDecision.DENY
        assert "supervision" in result.reason.lower()

    def test_lower_secondary_allowed_with_teacher(self):
        req = AccessRequest(
            student=Student("S2", "Bjorn", grade=9, age=15),
            tool_name="Claude",
            timestamp="2026-06-20T10:00:00+00:00",
            teacher_present=True,
        )
        result = self.engine.check(req)
        assert result.decision == AccessDecision.ALLOW
        assert "supervision" in result.reason.lower()

    def test_upper_secondary_allowed(self):
        req = AccessRequest(
            student=Student("S3", "Clara", grade=12, age=18),
            tool_name="Gemini",
            timestamp="2026-06-20T10:00:00+00:00",
            teacher_present=False,
        )
        result = self.engine.check(req)
        assert result.decision == AccessDecision.ALLOW


class TestTeacherOverride:
    def setup_method(self):
        self.engine = PolicyEngine()
        self.engine.load_norway_defaults()

    def test_override_allows_elementary(self):
        self.engine.grant_teacher_override("S1", "ChatGPT")
        req = AccessRequest(
            student=Student("S1", "Ada", grade=5, age=10),
            tool_name="ChatGPT",
            timestamp="2026-06-20T10:00:00+00:00",
        )
        result = self.engine.check(req)
        assert result.decision == AccessDecision.ALLOW
        assert "override" in result.reason.lower()

    def test_override_specific_to_tool(self):
        self.engine.grant_teacher_override("S1", "ChatGPT")
        req = AccessRequest(
            student=Student("S1", "Ada", grade=5, age=10),
            tool_name="Claude",
            timestamp="2026-06-20T10:00:00+00:00",
        )
        result = self.engine.check(req)
        assert result.decision == AccessDecision.DENY

    def test_revoke_override(self):
        self.engine.grant_teacher_override("S1", "ChatGPT")
        self.engine.revoke_teacher_override("S1", "ChatGPT")
        req = AccessRequest(
            student=Student("S1", "Ada", grade=5, age=10),
            tool_name="ChatGPT",
            timestamp="2026-06-20T10:00:00+00:00",
        )
        result = self.engine.check(req)
        assert result.decision == AccessDecision.DENY


class TestDailyLimits:
    def test_daily_limit_enforced(self):
        engine = PolicyEngine()
        from datetime import time as time_mod
        engine.set_policy(AccessPolicy(
            grade_band=GradeBand.UPPER_SECONDARY,
            default_decision=AccessDecision.ALLOW,
            max_daily_requests=2,
        ))

        student = Student("S3", "Clara", grade=12, age=18)
        ts_base = "2026-06-20T10:00:00+00:00"

        for i in range(2):
            req = AccessRequest(student=student, tool_name="ChatGPT", timestamp=f"{ts_base}{i}")
            result = engine.check(req)
            assert result.decision == AccessDecision.ALLOW

        # Third request should be denied
        req = AccessRequest(student=student, tool_name="ChatGPT", timestamp=f"{ts_base}3")
        result = engine.check(req)
        assert result.decision == AccessDecision.DENY
        assert "limit" in result.reason.lower()

    def test_daily_count_tracking(self):
        engine = PolicyEngine()
        engine.set_policy(AccessPolicy(
            grade_band=GradeBand.UPPER_SECONDARY,
            default_decision=AccessDecision.ALLOW,
            max_daily_requests=10,
        ))
        student = Student("S3", "Clara", grade=12, age=18)
        req = AccessRequest(student=student, tool_name="ChatGPT", timestamp="2026-06-20T10:00:00+00:00")
        engine.check(req)
        assert engine.get_daily_count("S3", "2026-06-20") == 1


class TestNoPolicyConfigured:
    def test_default_deny_without_policy(self):
        engine = PolicyEngine()
        req = AccessRequest(
            student=Student("S1", "Ada", grade=5, age=10),
            tool_name="ChatGPT",
            timestamp="2026-06-20T10:00:00+00:00",
        )
        result = engine.check(req)
        assert result.decision == AccessDecision.DENY
