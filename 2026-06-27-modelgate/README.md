# ModelGate — AI Model Access Governance

**Who can use which AI model?** ModelGate manages tiered access controls for AI model
usage within organizations — with audit trails, compliance reporting, and government
vetting-ready exports.

Built in response to the GPT-5.6 / Anthropic Mythos government vetting requirements
(June 2026): the US government now requires vetting of users accessing the most
capable AI models. Organizations need a tool to manage who can access which model tier,
track usage, and generate compliance reports.

## Why This Exists

Existing tools don't address the new governance gap:

| Tool | What It Does | Gap |
|------|-------------|-----|
| `ai-governance` (PyPI) | Empty stub (0.0.3) | Does nothing |
| Okta / Azure AD | Generic SSO | No model-tier awareness |
| RegShield | AI regulatory compliance | Regulatory scanning, not access control |
| AgentIAM | Agent identity management | Agent-to-agent, not human-to-model |

**ModelGate** is specifically about **human→model access governance**: which employees
can access which AI model tiers, with full audit trails and government-compliance-ready
reporting.

## Features

- **Tiered Model Registry** — Define model tiers (Public, Restricted, Classified, Government-Vetted)
- **Employee Access Policies** — Assign employees to model tiers with justification and expiry dates
- **Access Requests & Approvals** — Workflow for requesting access to restricted models
- **Usage Audit Trail** — Every model access logged with timestamp, employee, model, and purpose
- **Compliance Reports** — Government-ready exports showing who accessed what, when, and why
- **Access Reviews** — Scheduled review of access policies to prevent privilege creep
- **CLI Interface** — Full command-line access for admins and compliance officers

## Installation

```bash
pip install modelgate
```

## Quick Start

```bash
# Initialize with default tiers
modelgate init

# Register an employee
modelgate employee add --email alice@company.com --name "Alice Chen" --department Engineering

# Grant access to a tier
modelgate access grant --email alice@company.com --tier restricted --justification "Working on GPT-5.6 integration" --approver boss@company.com

# Log a model access
modelgate log --email alice@company.com --model gpt-5.6 --purpose "Customer support automation"

# Generate compliance report
modelgate report --format csv --since 2026-06-01

# Review access (find expiring/expired grants)
modelgate review
```

## Model Tiers

| Tier | Description | Example Models |
|------|-------------|---------------|
| `public` | Freely available models | GPT-4o-mini, Claude Haiku, Gemini Flash |
| `restricted` | Usage-restricted by provider | GPT-4o, Claude Sonnet, Gemini Pro |
| `classified` | Government-vetted access required | GPT-5.6, Anthropic Mythos |
| `government_vetted` | Explicit government clearance | Models with national security implications |

## Architecture

- **SQLite backend** — Zero-config persistence for audit trails and access policies
- **Immutable audit log** — Access records cannot be modified or deleted
- **Policy engine** — Tiered access rules with approval workflows
- **Compliance exporter** — CSV and JSON reports for regulatory submission

## License

MIT
