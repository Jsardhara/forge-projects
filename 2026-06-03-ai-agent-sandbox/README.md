# AI Agent Security Sandbox

> Lightweight security toolkit for AI agents — API key vault, network egress control, filesystem sandbox, and audit logging.

## Problem

AI agents are being deployed rapidly, but security tooling hasn't kept up:
- **AI worms** can target any online device (U of T research, 2026)
- **VSCode token-stealing** bug exposed GitHub credentials (402 HN points)
- **Microsoft Execution Containers** just launched at Build 2026 — proving the market demand

Yet no dominant, self-hosted, open-source tool exists for securing AI agents at the local level.

## Solution

This toolkit provides defense-in-depth for AI agents running on your machine:

| Feature | What it does |
|---------|-------------|
| **API Key Vault** | Scoped permissions (by model, endpoint), SHA-256 hashed storage, usage tracking |
| **Network Egress Control** | Domain allowlist (default-deny), blocks unauthorized outbound calls |
| **Filesystem Sandbox** | Restrict agents to allowed directories, log all file access attempts |
| **Audit Logger** | Centralized, queryable audit trail; export to JSON for compliance |
| **Kill Switch** | One-click emergency stop — instantly blocks all network egress |

## Quick Start

```bash
pip install -e ".[dev]"

from ai_agent_sandbox.sandbox import Sandbox, SandboxConfig
from ai_agent_sandbox.vault import KeyScope

sb = Sandbox(SandboxConfig(
    agent_id="my-agent",
    allowed_dirs=["/home/user/projects"],
    allowed_domains=["api.openai.com", "api.anthropic.com"],
))

sb.load_key("OPENAI_API_KEY", name="openai", scope=KeyScope(
    allowed_models=("gpt-4", "gpt-3.5-turbo"),
))

# Check network access
sb.check_network("https://api.openai.com/v1/chat")  # True
sb.check_network("https://evil.com/steal")             # False

# Emergency stop
sb.kill()

# Review audit trail
print(sb.audit_summary())
```

## Security Model

```
┌──────────────────────────────────────────────┐
│                AI Agent                      │
│                                              │
│  ┌─────────────┐  ┌──────────────────────┐  │
│  │ API Key Vault│  │ Network Egress Ctrl  │  │
│  │ (scoped)     │  │ (domain allowlist)   │  │
│  └─────────────┘  └──────────────────────┘  │
│                                              │
│  ┌─────────────┐  ┌──────────────────────┐  │
│  │ Filesystem   │  │ Audit Logger         │  │
│  │ Sandbox      │  │ (JSON export)        │  │
│  └─────────────┘  └──────────────────────┘  │
│                                              │
│  ┌──────────────────────────────────────┐   │
│  │ Kill Switch (emergency stop)          │   │
│  └──────────────────────────────────────┘   │
└──────────────────────────────────────────────┘
```

## Testing

```bash
pytest tests/ -v
# 45 tests, all passing
```

## Roadmap

- [ ] Local HTTP proxy for transparent network interception
- [ ] Windows ETW / macOS DTrace integration for syscall monitoring
- [ ] Web dashboard for real-time agent monitoring
- [ ] Slack/email alerts for security violations
- [ ] Team management (multi-agent, multi-user)
- [ ] Cloud sync for audit logs

## License

MIT
