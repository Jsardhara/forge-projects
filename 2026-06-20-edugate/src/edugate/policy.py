"""Policy engine for age-gated AI access control."""

from __future__ import annotations

import dataclasses
import enum
from datetime import time


class GradeBand(enum.Enum):
    """Educational grade bands aligned with Norway's AI regulations."""
    ELEMENTARY = "elementary"       # Grades 1-7, ages 6-13
    LOWER_SECONDARY = "lower_secondary"  # Grades 8-10, ages 14-16
    UPPER_SECONDARY = "upper_secondary"  # Grades 11-13, ages 17-19


class AccessDecision(enum.Enum):
    """Result of an access check."""
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_SUPERVISION = "require_supervision"


@dataclasses.dataclass
class Student:
    """A student in the system."""
    student_id: str
    name: str
    grade: int  # 1-13 in Norwegian system
    age: int

    @property
    def grade_band(self) -> GradeBand:
        if self.grade <= 7:
            return GradeBand.ELEMENTARY
        elif self.grade <= 10:
            return GradeBand.LOWER_SECONDARY
        else:
            return GradeBand.UPPER_SECONDARY


@dataclasses.dataclass
class Teacher:
    """A teacher who can supervise AI access."""
    teacher_id: str
    name: str
    can_supervise: bool = True


@dataclasses.dataclass
class AccessPolicy:
    """Defines access rules for a grade band."""
    grade_band: GradeBand
    default_decision: AccessDecision
    allowed_hours_start: time | None = None  # None = no restriction
    allowed_hours_end: time | None = None
    requires_teacher_override: bool = False
    max_daily_requests: int | None = None


@dataclasses.dataclass
class AccessRequest:
    """A request to access an AI tool."""
    student: Student
    tool_name: str
    timestamp: str  # ISO format
    teacher_present: bool = False
    teacher_id: str | None = None


@dataclasses.dataclass
class PolicyResult:
    """Result of a policy evaluation."""
    decision: AccessDecision
    reason: str
    policy_matched: str


class PolicyEngine:
    """Evaluates access requests against configured policies."""

    def __init__(self) -> None:
        self._policies: dict[GradeBand, AccessPolicy] = {}
        self._teacher_overrides: dict[str, set[str]] = {}  # student_id -> set of tool_names
        self._daily_counts: dict[str, dict[str, int]] = {}  # date -> {student_id: count}

    def set_policy(self, policy: AccessPolicy) -> None:
        """Set the policy for a grade band."""
        self._policies[policy.grade_band] = policy

    def get_policy(self, band: GradeBand) -> AccessPolicy | None:
        """Get the policy for a grade band."""
        return self._policies.get(band)

    def grant_teacher_override(self, student_id: str, tool_name: str) -> None:
        """Allow a teacher to grant a student access to a specific tool."""
        if student_id not in self._teacher_overrides:
            self._teacher_overrides[student_id] = set()
        self._teacher_overrides[student_id].add(tool_name)

    def revoke_teacher_override(self, student_id: str, tool_name: str) -> None:
        """Revoke a teacher's override for a student."""
        if student_id in self._teacher_overrides:
            self._teacher_overrides[student_id].discard(tool_name)

    def check(self, request: AccessRequest) -> PolicyResult:
        """Evaluate an access request."""
        band = request.student.grade_band
        policy = self._policies.get(band)

        if policy is None:
            return PolicyResult(
                decision=AccessDecision.DENY,
                reason=f"No policy configured for grade band '{band.value}'",
                policy_matched="default_deny",
            )

        # Check teacher override
        if self._has_override(request.student.student_id, request.tool_name):
            return PolicyResult(
                decision=AccessDecision.ALLOW,
                reason="Teacher override granted",
                policy_matched="teacher_override",
            )

        # Check daily request limit
        if policy.max_daily_requests is not None:
            date_key = request.timestamp[:10]  # YYYY-MM-DD
            counts = self._daily_counts.setdefault(date_key, {})
            current = counts.get(request.student.student_id, 0)
            if current >= policy.max_daily_requests:
                return PolicyResult(
                    decision=AccessDecision.DENY,
                    reason=f"Daily request limit ({policy.max_daily_requests}) reached",
                    policy_matched=f"daily_limit_{band.value}",
                )

        # Apply default decision with supervision logic
        if policy.default_decision == AccessDecision.REQUIRE_SUPERVISION:
            if request.teacher_present:
                self._increment_count(request)
                return PolicyResult(
                    decision=AccessDecision.ALLOW,
                    reason="Access granted under teacher supervision",
                    policy_matched=f"supervised_{band.value}",
                )
            else:
                return PolicyResult(
                    decision=AccessDecision.DENY,
                    reason="Teacher supervision required but no teacher present",
                    policy_matched=f"supervised_{band.value}",
                )

        if policy.default_decision == AccessDecision.ALLOW:
            self._increment_count(request)
            return PolicyResult(
                decision=AccessDecision.ALLOW,
                reason=f"Access allowed for grade band '{band.value}'",
                policy_matched=f"allow_{band.value}",
            )

        # Default deny
        return PolicyResult(
            decision=AccessDecision.DENY,
            reason=f"Access denied for grade band '{band.value}' per policy",
            policy_matched=f"deny_{band.value}",
        )

    def _has_override(self, student_id: str, tool_name: str) -> bool:
        return tool_name in self._teacher_overrides.get(student_id, set())

    def _increment_count(self, request: AccessRequest) -> None:
        date_key = request.timestamp[:10]
        counts = self._daily_counts.setdefault(date_key, {})
        counts[request.student.student_id] = counts.get(request.student.student_id, 0) + 1

    def get_daily_count(self, student_id: str, date: str) -> int:
        """Get the number of requests a student made on a given date."""
        return self._daily_counts.get(date, {}).get(student_id, 0)

    def load_norway_defaults(self) -> None:
        """Load Norway's August 2026 AI regulations as default policies."""
        self.set_policy(AccessPolicy(
            grade_band=GradeBand.ELEMENTARY,
            default_decision=AccessDecision.DENY,
        ))
        self.set_policy(AccessPolicy(
            grade_band=GradeBand.LOWER_SECONDARY,
            default_decision=AccessDecision.REQUIRE_SUPERVISION,
        ))
        self.set_policy(AccessPolicy(
            grade_band=GradeBand.UPPER_SECONDARY,
            default_decision=AccessDecision.ALLOW,
        ))
