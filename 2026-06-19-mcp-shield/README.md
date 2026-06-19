# MCP Shield — Security for MCP Deployments

**Audit logging, policy enforcement, and compliance reporting for Model Context Protocol (MCP) deployments.**

MCP Shield is a Python library that sits between your AI agents and MCP servers, providing:

- **Audit Logging** — Every tool call logged with agent identity, tool name, server ID, policy decision, and risk score
- **Policy Engine** — Rule-based allow/deny with agent/tool/server pattern matching, rate limiting, and time windows
- **Compliance Reports** — SOC 2, GDPR, ISO 27001, and HIPAA-ready audit summaries with findings and recommendations

## Quick Start

```python
from mcp_shield import MCPShield, PolicyRule, PolicyAction

shield = MCPShield()

# Add policy rules
shield.add_policy_rule(PolicyRule(
    name="allow-read",
    action=PolicyAction.ALLOW,
    tool_pattern="read_*",
    priority=10,
))
shield.add_policy_rule(PolicyRule(
    name="deny-exec",
    action=PolicyAction.DENY,
    tool_pattern="exec",
    priority=20,
))

# Check a tool call
decision = shield.check(
    agent_id="agent-001",
    tool_name="read_file",
    server_id="dev-server",
    arguments={"path": "/tmp/test.txt"},
)
print(decision.action)  # PolicyAction.ALLOW

# Generate compliance report
report = shield.generate_compliance_report("agent-001")
print(report.is_compliant())
```

## Installation

```bash
pip install mcp-shield
```

For development:
```bash
pip install -e ".[dev]"
pytest tests/ -v
```

## Features

### Audit Logger
- Append-only event log with SHA-256 argument hashing
- Filter by agent, tool, severity, decision, or time range
- JSON export for SIEM integration
- Severity auto-calculated from risk score

### Policy Engine
- Rule-based allow/deny with glob pattern matching
- Rate limiting per agent+tool (calls per minute)
- Time window restrictions (business hours, etc.)
- Heuristic risk scoring based on tool type and arguments
- Default-require-approval (safe default)

### Compliance Reports
- SOC 2, GDPR, ISO 27001, HIPAA frameworks
- Automated findings with pass/fail/warning status
- Actionable recommendations
- JSON export for audit documentation

## CLI

```bash
mcp-shield demo        # Full demo
mcp-shield audit       # Audit logging demo
mcp-shield policy      # Policy engine demo
mcp-shield compliance  # Compliance report demo
```

## Architecture

```
Agent → MCPShield.check() → PolicyEngine.evaluate() → AuditLogger.log()
                                                        ↓
                                                   ComplianceReport
```

## License

MIT
