"""CLI for EduGate."""

from __future__ import annotations

import json as json_mod
import sys
from datetime import datetime, timezone


def main() -> None:
    """Entry point for the edugate CLI."""
    if len(sys.argv) < 2:
        _print_help()
        return

    command = sys.argv[1]
    if command == "demo":
        _run_demo()
    elif command == "policy":
        _show_policy()
    elif command == "audit":
        _show_audit()
    elif command == "compliance":
        _show_compliance()
    elif command == "help":
        _print_help()
    else:
        print(f"Unknown command: {command}")
        _print_help()


def _print_help() -> None:
    print("EduGate — AI Access Gateway for Schools")
    print()
    print("Usage: edugate <command>")
    print()
    print("Commands:")
    print("  demo        Run a demo access check scenario")
    print("  policy      Show current policy configuration")
    print("  audit       Show audit log summary")
    print("  compliance  Generate a Norway 2026 compliance report")
    print("  help        Show this help message")


def _run_demo() -> None:
    from edugate.audit import AuditLogger
    from edugate.gateway import Gateway
    from edugate.policy import (
        AccessRequest,
        Student,
    )

    gateway = Gateway(school_name="Demo Skole")
    gateway.policy.load_norway_defaults()

    # Scenario requests
    students = [
        Student("STU-001", "Ada", grade=5, age=10),
        Student("STU-002", "Bjorn", grade=9, age=15),
        Student("STU-003", "Clara", grade=12, age=18),
    ]
    tools = ["ChatGPT", "Claude", "Gemini"]
    ts = datetime.now(timezone.utc).isoformat()

    print("=== EduGate Demo ===\n")
    for student in students:
        for tool in tools:
            req = AccessRequest(
                student=student,
                tool_name=tool,
                timestamp=ts,
                teacher_present=(student.grade >= 8),
            )
            result = gateway.check_access(req)
            print(f"  {student.name} (grade {student.grade}) → {tool}: "
                  f"{result.decision.value.upper()} — {result.reason}")

    print(f"\n  ({len(students) * len(tools)} access checks performed)")
    print(f"\n  Audit: {gateway.audit.summary()}")


def _show_policy() -> None:
    from edugate.gateway import Gateway
    from edugate.policy import GradeBand

    gateway = Gateway(school_name="Demo")
    gateway.policy.load_norway_defaults()

    print("=== EduGate Policy Configuration ===\n")
    for band in GradeBand:
        policy = gateway.policy.get_policy(band)
        if policy:
            print(f"  {band.value}:")
            print(f"    Default: {policy.default_decision.value}")
            print(f"    Requires supervision: {policy.requires_teacher_override}")
            print(f"    Daily limit: {policy.max_daily_requests or 'unlimited'}")
        else:
            print(f"  {band.value}: NO POLICY SET")
        print()


def _show_audit() -> None:
    from edugate.audit import AuditLogger
    from edugate.gateway import Gateway
    from edugate.policy import AccessRequest, Student

    gateway = Gateway(school_name="Demo")
    gateway.policy.load_norway_defaults()
    ts = datetime.now(timezone.utc).isoformat()

    # Generate some events
    students = [
        Student("STU-001", "Ada", grade=5, age=10),
        Student("STU-002", "Bjorn", grade=9, age=15),
    ]
    for s in students:
        req = AccessRequest(student=s, tool_name="ChatGPT", timestamp=ts, teacher_present=False)
        gateway.check_access(req)

    summary = gateway.audit.summary()
    print("=== EduGate Audit Summary ===\n")
    for key, val in summary.items():
        print(f"  {key}: {val}")
    print()
    print("  Recent events:")
    for event in gateway.audit.events[-5:]:
        print(f"    [{event.decision.upper()}] {event.student_name} (grade {event.grade}) "
              f"→ {event.tool_name} — {event.reason}")


def _show_compliance() -> None:
    from edugate.audit import AuditLogger
    from edugate.gateway import Gateway
    from edugate.policy import AccessRequest, Student

    gateway = Gateway(school_name="Bergen Videregående")
    gateway.policy.load_norway_defaults()
    ts = datetime.now(timezone.utc).isoformat()

    # Simulate a day of activity
    scenarios = [
        Student("STU-001", "Ada", grade=5, age=10),
        Student("STU-002", "Bjorn", grade=5, age=11),
        Student("STU-003", "Clara", grade=9, age=15),
        Student("STU-004", "David", grade=9, age=15),
        Student("STU-005", "Eva", grade=12, age=18),
    ]
    tools = ["ChatGPT", "Claude", "Gemini"]
    for s in scenarios:
        for t in tools:
            req = AccessRequest(
                student=s, tool_name=t, timestamp=ts,
                teacher_present=(s.grade >= 8),
            )
            gateway.check_access(req)

    report = gateway.generate_compliance_report()
    print("=== EduGate Compliance Report ===\n")
    print(f"  Report ID: {report.report_id}")
    print(f"  Framework: {report.framework}")
    print(f"  School: {report.school_name}")
    print(f"  Generated: {report.generated_at}")
    print()
    for f in report.findings:
        icon = {"pass": "✅", "fail": "❌", "warning": "⚠️"}.get(f.status, "?")
        print(f"  {icon} [{f.control_id}] {f.description}")
        print(f"     Evidence: {f.evidence}")
        print()
    print(f"  Summary: {report.summary}")


if __name__ == "__main__":
    main()
