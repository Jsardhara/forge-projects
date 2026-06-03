# Monetization Plan — AI Agent Security Sandbox

## Revenue Model: SaaS + Open Core

### Tier 1: Free (Open Source)
- Core library (this repo): vault, egress, filesystem, audit
- Single agent, local only
- Community support

### Tier 2: Pro — $49/mo per user
- Web dashboard for real-time monitoring
- Slack/email alerts for violations
- Up to 5 agents
- JSON audit log export
- Email support

### Tier 3: Team — $199/mo (up to 10 agents)
- Everything in Pro
- Multi-user team management
- Centralized audit log (cloud-synced)
- Role-based access control
- Priority support

### Tier 4: Enterprise — Custom pricing
- Unlimited agents
- SSO/SAML integration
- Compliance reports (SOC 2, HIPAA)
- Custom integrations
- Dedicated support

## Market Timing

The convergence of three events in June 2026 creates a perfect window:
1. **Microsoft Execution Containers** at Build 2026 — validates the market
2. **U of T AI worm research** — proves the threat is real
3. **VSCode token-stealing bug** (402 HN points) — developer awareness is peak

No dominant self-hosted product exists. First-mover advantage: 2-3 weeks.

## Go-to-Market

1. **Launch on Product Hunt** — security angle + AI agent angle = viral potential
2. **Post on HN Show HN** — the 402pt token bug story proves audience interest
3. **Target r/LocalLLaMA** — developers running local agents need security
4. **Content marketing** — "How to secure your AI agent" blog posts
5. **Affiliate partnerships** — recommend Proton Mail, 1Password for key management

## Competitive Landscape

| Product | Approach | Weakness |
|---------|----------|----------|
| Microsoft Execution Containers | Windows-only, closed source | Not self-hosted, not open |
| agent-sandbox (PyPI) | Cloud API wrapper | Not local-first, not a security tool |
| Docker | Container overhead | Too heavy for CLI agents |

**Our advantage:** Lightweight, self-hosted, open-source core, works with any agent framework.

## Revenue Projections (Conservative)

- Month 1-3: 0 → 50 Pro users ($2,450/mo)
- Month 4-6: 50 → 200 Pro + 10 Team ($14,900/mo)
- Month 7-12: 200 → 1,000 Pro + 50 Team + 5 Enterprise ($89,500/mo)

**Year 1 ARR: ~$500K** (conservative, assuming 5% conversion from free users)
