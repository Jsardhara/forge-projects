# Monetization Plan — AI Leak Scanner

## Target Market

- **Primary**: Security teams at mid-to-large enterprises using AI extensions
- **Secondary**: DevSecOps engineers, CISOs, compliance officers
- **Tertiary**: Individual developers / indie hackers who want to audit their own setup

## Revenue Model: Freemium API

### Free Tier — "Personal Audit"
- CLI tool (open source, self-hosted)
- Up to 10 scans/month via API
- Public vulnerability database (24-hour delay on new entries)
- Community Discord support

**Price: $0**
**Goal**: Adoption, community, word-of-mouth

### Pro Team — "Continuous Monitoring"
- Unlimited scans via API
- Real-time vulnerability database updates
- Slack/Discord webhook alerts for new vulnerabilities
- CSV/PDF compliance reports
- Email support

**Price: $29/mo per team (up to 10 users)**
**Target**: Small security teams, dev shops

### Enterprise — "Full Compliance Pipeline"
- Everything in Pro
- SSO/SAML integration
- Custom vulnerability feeds (private disclosures)
- CI/CD pipeline integration (GitHub Actions, GitLab CI)
- SOC 2 / ISO 27001 compliance report templates
- Dedicated account manager
- SLA guarantees
- On-premise deployment option

**Price: $199/mo per organization**
**Target**: Enterprise security teams, compliance-heavy industries

## Go-to-Market

1. **Launch day**: Post to HN (the vulnerability story is already at 391 pts today)
2. **Week 1**: Write a blog post: "We built a scanner for the AI extension vulnerabilities nobody's talking about"
3. **Week 2**: Submit to Product Hunt, Hacker News Show
4. **Month 1**: Partner with PromptArmor for co-marketing (they have the research, we have the tool)
5. **Month 2**: Add Chrome extension manifest scanner (scan any extension before installing)
6. **Month 3**: Enterprise compliance reports (SOC 2 mapping)

## Competitive Landscape

| Tool | What They Do | What We Do |
|------|-------------|------------|
| PromptArmor | Research & disclosure | Scanning & monitoring |
| Snyk | Code dependency scanning | AI extension scanning |
| Changelog | Security news | Actionable vulnerability data |
| OpenSSF Scorecard | Open source security | AI agent security |

**Nobody is doing AI extension security scanning.** We're first.

## Revenue Projections

- **Month 1-3**: 0 revenue (build, launch, iterate)
- **Month 4-6**: 50 Pro teams = $1,450/mo
- **Month 7-12**: 200 Pro teams + 10 Enterprise = $7,700/mo
- **Year 2**: 1,000 Pro + 50 Enterprise = $39,500/mo

## Key Metrics to Track

- API scans per day
- Free → Pro conversion rate
- Enterprise pipeline
- Database coverage (vulnerabilities tracked)
- Time-to-detect (how fast we add new vulns after disclosure)

## What's Blocking Revenue Right Now

1. ✅ MVP built and tested
2. ⬜ Deploy API to Fly.io/Render
3. ⬜ Stripe billing integration
4. ⬜ User accounts + API key management
5. ⬜ Rate limiting middleware
6. ⬜ Landing page (GitHub Pages)
7. ⬜ Slack webhook alerts
8. ⬜ CI/CD integration templates
