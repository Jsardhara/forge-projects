"""CLI for MCP Shield — audit inspection, policy management, and compliance reports."""

from __future__ import annotations

import json
import sys
from typing import Optional

from .audit import AuditLogger, AuditSeverity
from .policy import PolicyEngine, PolicyRule, PolicyAction
from .compliance import ComplianceStandard, generate_report
from .shield import MCPShield


def main():
    """Entry point for mcp-shield CLI."""
    if len(sys.argv) < 2:
        _print_help()
        return

    command = sys.argv[1]

    if command == "demo":
        _run_demo()
    elif command == "audit":
        _run_audit_demo()
    elif command == "policy":
        _run_policy_demo()
    elif command == "compliance":
        _run_compliance_demo()
    elif command == "help":
        _print_help()
    else:
        print(f"Unknown command: {command}")
        _print_help()


def _run_demo():
    """Run a full demo: policy check → audit log → compliance report."""
    shield = MCPShield()

    # Add policy rules
    shield.add_policy_rule(PolicyRule(
        name="allow-read",
        action=PolicyAction.ALLOW,
        agent_pattern="agent-*",
        tool_pattern="read_*",
        server_pattern="*",
        priority=10,
    ))
    shield.add_policy_rule(PolicyRule(
        name="deny-shell",
        action=PolicyAction.DENY,
        agent_pattern="*",
        tool_pattern="exec",
        server_pattern="*",
        priority=20,
    ))
    shield.add_policy_rule(PolicyRule(
        name="deny-dangerous",
        action=PolicyAction.DENY,
        agent_pattern="*",
        tool_pattern="*",
        server_pattern="prod-*",
        priority=15,
    ))

    # Simulate tool calls
    calls = [
        ("agent-001", "read_file", "dev-server", {"path": "/tmp/test.txt"}),
        ("agent-001", "exec", "dev-server", {"command": "ls -la"}),
        ("agent-002", "read_config", "prod-server", {}),
        ("agent-001", "write_file", "dev-server", {"path": "/tmp/out.txt", "content": "hello"}),
        ("agent-003", "exec", "prod-server", {"command": "sudo rm -rf /"}),
    ]

    print("=== MCP Shield Demo ===\n")
    for agent, tool, server, args in calls:
        decision = shield.check(
            agent_id=agent,
            tool_name=tool,
            server_id=server,
            arguments=args,
        )
        status = "✓" if decision.action == PolicyAction.ALLOW else "✗"
        print(f"  {status} {agent} → {tool}@{server}: {decision.action.value} ({decision.reason})")

    # Summary
    summary = shield.get_audit_summary()
    print(f"\n=== Audit Summary ===")
    print(f"  Total events: {summary['total']}")
    print(f"  By decision: {summary['by_decision']}")
    print(f"  By severity: {summary['by_severity']}")
    print(f"  Avg risk: {summary['avg_risk']}")

    # Compliance report
    report = shield.generate_compliance_report("agent-001")
    print(f"\n=== Compliance Report (SOC 2) ===")
    print(f"  Agent: {report.agent_id}")
    print(f"  Compliant: {report.is_compliant()}")
    print(f"  Findings: {report.summary()['findings']}")
    for rec in report.recommendations:
        print(f"  → {rec}")


def _run_audit_demo():
    """Demonstrate audit logging capabilities."""
    audit = AuditLogger()

    # Log some events
    audit.log(
        agent_id="agent-001",
        tool_name="read_file",
        server_id="server-a",
        arguments={"path": "/data/test.txt"},
        action="tool_call",
        decision="allow",
        risk_score=0.1,
    )
    audit.log(
        agent_id="agent-001",
        tool_name="exec",
        server_id="server-a",
        arguments={"command": "sudo rm -rf /"},
        action="tool_call",
        decision="deny",
        risk_score=0.95,
        reason="Dangerous command pattern detected",
    )
    audit.log(
        agent_id="agent-002",
        tool_name="database_query",
        server_id="prod-db",
        arguments={"query": "SELECT * FROM users"},
        action="tool_call",
        decision="allow",
        risk_score=0.4,
    )

    print("=== Audit Log Demo ===\n")
    print(f"Total events: {audit.count}")
    print(f"Critical events: {len(audit.get_critical_events())}")
    print(f"\nBy agent:")
    for agent in ["agent-001", "agent-002"]:
        events = audit.filter_by_agent(agent)
        print(f"  {agent}: {len(events)} events")

    print(f"\nSummary: {json.dumps(audit.summary(), indent=2)}")


def _run_policy_demo():
    """Demonstrate policy engine capabilities."""
    engine = PolicyEngine([
        PolicyRule(
            name="allow-read",
            action=PolicyAction.ALLOW,
            agent_pattern="agent-*",
            tool_pattern="read_*",
            priority=10,
        ),
        PolicyRule(
            name="deny-exec",
            action=PolicyAction.DENY,
            agent_pattern="*",
            tool_pattern="exec",
            priority=20,
        ),
        PolicyRule(
            name="rate-limited-fetch",
            action=PolicyAction.ALLOW,
            agent_pattern="*",
            tool_pattern="fetch",
            max_calls_per_minute=5,
            priority=5,
        ),
    ])

    print("=== Policy Engine Demo ===\n")
    tests = [
        ("agent-001", "read_file", "server-a", {}),
        ("agent-001", "exec", "server-a", {}),
        ("agent-002", "write_file", "server-b", {}),
    ]

    for agent, tool, server, args in tests:
        decision = engine.evaluate(
            agent_id=agent, tool_name=tool, server_id=server, arguments=args,
        )
        print(f"  {agent} → {tool}@{server}: {decision.action.value} ({decision.reason})")

    # Test rate limiting
    print(f"\n  Rate limit test (6 rapid fetch calls):")
    for i in range(6):
        d = engine.evaluate(agent_id="agent-001", tool_name="fetch", server_id="s1")
        print(f"    Call {i+1}: {d.action.value}")


def _run_compliance_demo():
    """Demonstrate compliance report generation."""
    shield = MCPShield()
    shield.add_policy_rule(PolicyRule(
        name="allow-read",
        action=PolicyAction.ALLOW,
        agent_pattern="*",
        tool_pattern="read_*",
        priority=10,
    ))
    shield.add_policy_rule(PolicyRule(
        name="deny-exec",
        action=PolicyAction.DENY,
        agent_pattern="*",
        tool_name="exec",
        priority=20,
    ))

    # Generate some traffic
    for _ in range(5):
        shield.check(agent_id="agent-001", tool_name="read_file", server_id="dev", arguments={"path": "/x"})
    shield.check(agent_id="agent-001", tool_name="exec", server_id="dev", arguments={"command": "ls"})
    shield.check(agent_id="agent-001", tool_name="read_config", server_id="dev", arguments={})

    print("=== Compliance Report Demo ===\n")
    for std in [ComplianceStandard.SOC2, ComplianceStandard.GDPR]:
        report = shield.generate_compliance_report("agent-001", standard=std)
        print(f"--- {std.value.upper()} ---")
        print(f"  Compliant: {report.is_compliant()}")
        print(f"  Total events: {report.total_events}")
        print(f"  Critical: {report.critical_events}")
        print(f"  Denied: {report.denied_events}")
        for f in report.findings:
            print(f"  [{f.status.upper()}] {f.control}: {f.description}")
        for rec in report.recommendations:
            print(f"  → {rec}")
        print()


def _print_help():
    print("MCP Shield — Security for MCP deployments")
    print()
    print("Usage: mcp-shield <command>")
    print()
    print("Commands:")
    print("  demo        Run full demo (policy + audit + compliance)")
    print("  audit       Demo audit logging")
    print("  policy      Demo policy engine")
    print("  compliance  Demo compliance reports")
    print("  help        Show this help")
