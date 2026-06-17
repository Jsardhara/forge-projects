# JUSTIFICATION.md

## AgentIAM — AI Agent Identity & Access Management

### The Problem
AI agents are proliferating across enterprises — booking travel, processing payments, accessing customer data, calling APIs. Yet only 18% of security leaders trust their existing IAM systems to handle agent identities, and only 23% have a formal agent identity strategy (Cloud Security Alliance, 2026). Agents don't fit traditional IAM: they're autonomous, short-lived, self-updating, span multiple platforms simultaneously, and operate continuously with no human present to re-authenticate.

Existing solutions (AgentArmor, LoginRadius Agentic IAM, Curity) are either broad security frameworks where identity is one layer among many, or expensive enterprise SaaS. There's no focused, open-source Python library specifically for agent identity lifecycle management.

### Who's the User
- Platform engineers deploying AI agents who need to manage credentials, rotate secrets, enforce least-privilege access, and maintain audit trails
- Security teams who need to govern agent behavior with the same rigor as human users
- DevOps teams who need to register, provision, suspend, and revoke agent identities programmatically

### Why Existing Solutions Are Inadequate
- **AgentArmor**: L8 Identity is one of 8 layers — not a dedicated IAM tool
- **Enterprise IAM (Okta, Azure AD)**: Built for humans, not autonomous agents
- **OAuth 2.0 alone**: Handles delegation but not full identity lifecycle
- **Shared credentials**: Tokens passed to agents with no rotation, no scope binding, no audit — a growing attack surface

### Success Criteria
- Agent registration with unique identities bound to verifiable claims (code signature, model hash)
- Short-lived, scope-bound credential issuance with automatic rotation
- Policy engine for risk-based, context-aware access decisions
- Full audit trail tying every action to an agent identity
- CLI + Python library for easy integration into CI/CD and agent frameworks

### Lens Research Support
- HN Top Story: "Running local models is good now" — more agents running locally = more need for local IAM
- CoSAI Agentic IAM paper (March 2026): Calls for short-lived, unique agent identities bound to verifiable claims
- CSA Survey 2026: 55% cite sensitive data exposure as top concern; 40% increasing identity budgets
- Opportunity #1 from Lens Daily Intel 2026-06-17: "AI Agent Identity & Access Management (AgentIAM)"
