# Project Justification — ModelGate

On June 26, 2026, OpenAI announced that the US government will vet users of GPT-5.6, their most capable model. The same day, the Trump administration released Anthropic's Mythos model to 100+ "trusted" US companies and agencies after the NSA confirmed it breached classified systems. This creates an unprecedented governance gap: organizations need to control **which employees can access which AI model tier**, track every access, and produce compliance reports for government auditors. No existing tool addresses this — Okta/Azure AD handle generic SSO but lack model-tier awareness; PyPI's `ai-governance` is an empty stub; RegShield scans for regulatory compliance but doesn't manage human→model access; AgentIAM manages agent identity, not human access. ModelGate fills this gap: a tiered model access governance tool with audit trails, approval workflows, and government-compliance-ready reporting.

**User**: Compliance officers and IT admins at companies using powerful AI models
**Why existing solutions fail**: None combine model-tier-awareness + approval workflow + immutable audit + compliance export
**Success metric**: A compliance officer can generate a complete access report showing who accessed GPT-5.6 and why, in under 30 seconds
