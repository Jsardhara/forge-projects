# AgentIAM — AI Agent Identity & Access Management

A focused Python library for managing AI agent identities, short-lived credentials,
policy-based access control, and audit trails.

## Why AgentIAM?

AI agents are proliferating — booking travel, processing payments, calling APIs, accessing data.
Yet only 18% of security leaders trust their existing IAM for agents, and only 23% have a
formal agent identity strategy (Cloud Security Alliance, 2026).

Traditional IAM was built for humans. Agents are autonomous, short-lived, self-updating, and
span multiple platforms. AgentIAM gives them first-class identity.

## Features

- **Identity Registry**: Register agents with unique IDs bound to verifiable claims (code hash, model ID)
- **Short-Lived Credentials**: Scope-bound tokens with automatic expiry and rotation
- **Policy Engine**: RBAC/ABAC-style policies with chain depth limits, scope allow/deny lists, human-in-the-loop gates
- **Audit Log**: Append-only log tying every action to an agent identity
- **CLI**: Full command-line interface for scripting and CI/CD

## Quick Start

```python
from agentiam import AgentIAM

iam = AgentIAM(default_credential_ttl=3600)

# Register an agent
agent = iam.register_agent(
    name="travel-booker",
    owner="platform-team",
    description="Books flights and hotels",
    model_id="openai/gpt-4o",
    scopes=["travel:read", "travel:book"],
)

# Issue a credential
cred = iam.iam.issue_credential(agent.agent_id)

# Validate
validated = iam.validate_credential(cred.token)
print(f"Agent {validated.agent_id} authenticated, scopes: {validated.scopes}")

# Create a policy
policy = iam.policies.create_policy(
    name="travel-policy",
    allowed_scopes=["travel:read", "travel:book"],
    denied_scopes=["admin:*"],
    max_chain_depth=2,
)

# Check access
allowed, reason = iam.check_access(cred.token, ["travel:book"], policy.policy_id)
print(f"Access: {allowed} ({reason})")

# Revoke agent (also revokes all credentials)
iam.revoke_agent(agent.agent_id)
```

## CLI

```bash
# Install
pip install -e ".[dev]"

# Register an agent
agentiam register --name travel-booker --owner platform-team --scopes travel:read travel:book

# Issue a credential
agentiam issue --agent-id agent-abc123 --scopes travel:book --ttl 1800

# Validate a token
agentiam validate --token <token>

# View audit log
agentiam audit --limit 20
```

## Architecture

```
AgentIAM (facade)
├── IdentityRegistry    — agent CRUD, status management
├── CredentialManager   — issue, validate, rotate, revoke
├── PolicyEngine        — scope-based access decisions
└── AuditLog            — append-only event log
```

## Research Basis

- CoSAI Agentic IAM Paper (March 2026): Short-lived, unique identities bound to verifiable claims
- Cloud Security Alliance Survey 2026: 55% cite sensitive data exposure as top agent risk
- OWASP ASI (Agentic Security Integrity) 10 risks — AgentIAM covers identity, credential, and audit layers

## License

MIT
