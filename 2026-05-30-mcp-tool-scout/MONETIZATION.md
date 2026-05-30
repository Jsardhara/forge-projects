# Monetization Plan — MCP Tool Scout

## Revenue Model

### 1. Freemium API (Primary)
- **Free tier**: 100 requests/day, seed data only
- **Pro tier** ($29/mo): 10K requests/day, live GitHub data, webhooks
- **Team tier** ($99/mo): Unlimited, team dashboard, Slack integration

### 2. MCP Directory / Marketplace
- Listed servers can pay for "verified" badges ($49/mo)
- Featured placement in search results ($199/mo)
- Analytics dashboard for server maintainers ($29/mo)

### 3. Enterprise Self-Hosted
- One-time license ($500-2000) for internal deployment
- Annual support contract ($1000/yr)

### 4. Affiliate / Referral Revenue
- Link to hosting services (Railway, Render, Fly.io) for one-click deploy
- Affiliate commissions on infrastructure referrals

## Market Sizing

- **MCP ecosystem**: ~500+ servers as of mid-2026, growing 30%+ MoM
- **Target developers**: ~50K+ AI agent developers (conservative)
- **Conversion**: 2-5% to paid tiers = 1,000-2,500 paying users
- **ARR potential**: $350K-$900K at scale

## Go-to-Market

### Phase 1 (Week 1-2): Launch & Seed
- Deploy to Fly.io/Render (free tier)
- Post on HN, Reddit r/LocalLLaMA, MCP Discord
- Submit to awesome-mcp lists

### Phase 2 (Week 3-4): Community
- Add "Submit your MCP server" form
- Build Slack bot: `/mcp-search postgres`
- Weekly "Top MCP Servers" newsletter

### Phase 3 (Month 2+): Monetize
- Add Stripe billing for Pro/Team tiers
- Partner with MCP server authors for co-marketing
- Build maintainer analytics dashboard

## Competitive Advantage

No direct competitor exists today. Closest alternatives:
- **awesome-mcp GitHub lists**: Manual, no scoring, no API
- **MCP marketplace (official)**: Basic listing, no scoring

MCP Tool Scout is first-mover in MCP server discovery + evaluation.

## Next Steps After MVP

1. Deploy live API (Fly.io)
2. Add real-time GitHub webhook sync
3. Build maintainer profiles + verification
4. Add user accounts + API key management
5. Implement Stripe billing
