# Monetization Plan — AI Cost Guard

## Revenue Model: SaaS Freemium

### Free Tier (Individuals)
- Single team, up to 3 API keys
- Daily/weekly budgets
- Basic waste detection
- CLI + API access
- Community support

### Pro Tier — $29/mo per team
- Unlimited API keys
- Monthly budgets + custom periods
- Advanced waste detection with savings projections
- Web dashboard with historical trends
- Slack/email alert integrations
- Priority support

### Team Tier — $99/mo (up to 10 teams)
- Everything in Pro
- Multi-team cost allocation
- SSO/SAML
- Audit logs
- Custom pricing data
- API rate limits: 10K calls/hour

### Enterprise — Custom pricing
- Unlimited teams
- On-premise deployment
- Custom model pricing
- SLA guarantees
- Dedicated support

## Market Opportunity

- **TAM**: Every company using AI APIs (OpenAI, Anthropic, Google) — estimated 500K+ companies globally
- **SAM**: Mid-market teams (10-500 employees) with >$1K/month AI spend — ~50K companies
- **SOM**: Early adopters in tech-forward companies — ~5K companies in Year 1

## Competitive Landscape

| Tool | Pricing | Weakness |
|------|---------|----------|
| OpenAI Usage Dashboard | Free | OpenAI only, no budgets/alerts |
| Anthropic Console | Free | Anthropic only, no waste detection |
| LiteLLM | Open source | Complex setup, no dashboard |
| Helicone | $50/mo+ | Proxy-based, privacy concerns |
| **AI Cost Guard** | **Free → $29/mo** | **Multi-provider, waste detection, simple** |

## Go-to-Market

1. **Launch on Product Hunt** — Free tier as lead magnet
2. **GitHub open source** — Build community, get contributions
3. **Content marketing** — "How we saved $4,200/month on AI bills" case studies
4. **Integration partnerships** — Bundle with AI dev tools
5. **Viral loop** — Waste report shows "You could save $X/month" → shareable

## Unit Economics

- **CAC**: $15 (content + Product Hunt)
- **LTV**: $348 (12 months × $29/mo, 5% churn)
- **LTV:CAC**: 23x
- **Gross margin**: 95% (self-hosted, minimal infra)

## Milestones

| Milestone | Target | Timeline |
|-----------|--------|----------|
| MVP launch | Product Hunt top 10 | Month 1 |
| 1,000 free users | GitHub stars + signups | Month 3 |
| 100 paying teams | $2,900 MRR | Month 6 |
| 500 paying teams | $14,500 MRR | Month 12 |
| Break-even | Cover hosting + dev costs | Month 4 |

## What's Still Needed for Revenue-Ready

1. **Stripe integration** — Payment processing for Pro/Team tiers
2. **User auth** — Signup/login with team management
3. **Hosted dashboard** — Deploy on Fly.io or Railway
4. **Slack integration** — Post alerts to Slack channels
5. **Email digests** — Weekly spend summary emails
6. **Historical charts** — Spend over time in dashboard
7. **API key management** — Encrypted storage of API keys
8. **Rate limiting** — Per-team API rate limits
