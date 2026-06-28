# Project Justification: ZeroDaySentinel

## Problem
On June 27-28, 2026, anonymous mass 0-day vulnerability drops began appearing on GitHub at unprecedented scale (HN #7 and #3, both 811+ points). The "exploitarium" repository by user "bikini" is systematically publishing weaponized exploits for undisclosed vulnerabilities. Security teams at affected companies have **zero automated tooling** to detect when their dependencies are hit by 0-day disclosures, generate patch suggestions, and coordinate response.

Existing tools (Dependabot, Snyk, OSV) track *known* CVEs. They do not detect *undisclosed* 0-day drops in real-time. No open-source tool monitors GitHub for new exploit/0-day repositories, fingerprints the disclosed vulnerabilities against a company's dependency graph, and generates AI-assisted patch suggestions.

## User
Security engineers, DevOps leads, and CTOs at mid-to-large companies who need to know within minutes — not days — that a zero-day exploit has been published affecting their stack.

## Why Existing Solutions Are Inadequate
- **GitHub Advisory Database**: Only covers disclosed, patched CVEs. Useless for 0-days.
- **Snyk/Dependabot**: Reactive scanning against known vulnerabilities. Miss undisclosed exploits entirely.
- **CISA KEV**: Catalogs *known exploited* vulnerabilities but with days-to-weeks delay.
- **Manual monitoring**: Impossible to watch thousands of repos for new exploit publications.

## Success Metrics
- Detects new 0-day GitHub repo within 5 minutes of publication (via polling/webhook)
- Fingerprint matches against a dependency graph with >90% precision
- Generates actionable patch suggestions (not just alerts)
- Zero external dependencies for core detection logic (stdlib only)
