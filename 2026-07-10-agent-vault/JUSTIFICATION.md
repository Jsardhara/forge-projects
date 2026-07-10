# Project Justification — AgentVault (2026-07-10)

## Problem
AI coding/research agents with repo and API access leak secrets — a recurring 2026
incident theme (GitLost, Flint, n8n's "Agent Identity" post, Cloudflare Drop, and the
TC story of an agent that ran a $100M fundraise). The operator's own ecosystem runs
agents that touch Alpaca keys (atlas), Stripe (signal-feed), and GitHub tokens
(forge-projects). Today there is no lightweight, dependency-free control plane that
(1) issues *scoped, revocable, short-lived* credentials to an agent session instead
of handing it the real secret, (2) filters outbound (egress) traffic to an
allowlist, and (3) produces a tamper-evident audit log of every secret access.

## User
Developers and platform teams running autonomous/semi-autonomous agents (CI coding
agents, research agents, MCP servers) who need to enforce least-privilege credential
handling and prove (to auditors/customers) that secrets were not exfiltrated. Also
directly useful inside this very Jarmes/Forge system as a guardrail pattern.

## Why existing solutions are inadequate
- `ai-agent-sandbox` (06-03) and `agentos` (06-15) sandbox *execution* but do not
  manage *credential lifecycle* (scoping/expiry/revocation) or egress policy.
- `mcp-shield` (06-19) is a policy engine for MCP *tool calls*, not a credential
  broker + egress proxy for the agent's own network/runtime scope.
- `breach-sentinel` (06-30) detects breaches post-hoc; AgentVault is *preventive*
  (never hands out the real secret, blocks non-allowlisted egress).
- Managed offerings (Cloudflare Drop, 1Password/Infisical SDKs) require external
  accounts/infra. AgentVault is a zero-dependency, self-hostable library + CLI.

## Success criterion
A stdlib-only Python package where: (a) a vault can mint a scoped, expiring token or
inject an alias that maps to a real secret at use-time; (b) the operator can revoke
a session or a single secret instantly; (c) an egress filter decides allow/deny
against a host/port allowlist with wildcard + CIDR support; (d) every secret read is
recorded as a tamper-evident (chained SHA-256) audit entry; (e) unit + integration +
CLI tests pass. If the operator can drop it into a CI agent and get a deny-on-missing
allowlist + revocable session + signed audit trail, it succeeds.
