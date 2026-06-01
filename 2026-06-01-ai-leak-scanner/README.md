# AI Leak Scanner

**Security audit tool for AI extensions and agents — detect data exfiltration risks before they cost you.**

Born from the [ChatGPT for Google Sheets data exfiltration](https://www.promptarmor.com/resources/gpt-for-google-sheets-data-exfiltration) research (391 pts on HN, June 1 2026) and [PromptArmor's catalog](https://www.promptarmor.com) of 20+ AI data exfiltration vulnerabilities.

## The Problem

AI extensions are everywhere — ChatGPT for Sheets, Claude Cowork, Notion AI, Slack AI, GitHub Copilot CLI, and dozens more. Each one has broad permissions to your data. And they're being exploited:

- **ChatGPT for Google Sheets** — indirect prompt injection exfiltrates entire workbook collections
- **Claude Cowork** — malicious documents steal files from connected storage
- **Notion AI** — workspace data exfiltration via injected page content
- **GitHub Copilot CLI** — downloads and executes malware
- **Snowflake Cortex AI** — sandbox escape to full data warehouse access

These aren't theoretical. They're published, demonstrated attacks. And most organizations have no idea which of their AI extensions are vulnerable.

## What This Does

AI Leak Scanner maintains a database of known AI extension vulnerabilities and lets you:

1. **Scan your installed extensions** — find out which ones have known data exfiltration risks
2. **Get risk scores** — 0-100 scale with severity breakdowns
3. **Get mitigation guidance** — specific steps for each vulnerability
4. **Audit the full threat landscape** — see all 20+ known vulnerabilities

## Quick Start

```bash
# Install
pip install ai-leak-scanner

# Scan your extensions
ai-leak-scanner scan "ChatGPT for Google Sheets" "Claude Cowork" "Notion AI"

# Full threat landscape audit
ai-leak-scanner audit

# JSON output (for CI/CD pipelines)
ai-leak-scanner json "ChatGPT for Google Sheets"

# Start API server
ai-leak-scanner serve 8000
```

## API

```bash
# Start server
python -m ai_leak_scanner.app

# Health check
curl http://localhost:8000/health

# List all vulnerabilities
curl http://localhost:8000/vulns

# Scan extensions
curl -X POST http://localhost:8000/scan \
  -H "Content-Type: application/json" \
  -d '{"extensions": ["ChatGPT for Google Sheets", "Claude Cowork"]}'

# Get stats
curl http://localhost:8000/stats
```

## Vulnerability Database

20 vulnerabilities covering 13 vendors:

| Severity | Count |
|----------|-------|
| CRITICAL | 9     |
| HIGH     | 6     |
| MEDIUM   | 4     |
| Unpatched| 19    |

Vendors: OpenAI, Anthropic, Notion, Slack, GitHub, Snowflake, Superhuman, Microsoft, HuggingFace, Google, Ollama, Ramp, IBM, Writer, vLex

## Tech Stack

- Python 3.11+
- FastAPI (REST API)
- Pydantic (data models)
- Click (CLI)
- pytest (35 tests, all passing)

## Roadmap

- [ ] Chrome extension manifest scanner
- [ ] VS Code extension scanner
- [ ] Slack app permission auditor
- [ ] Automated CVE tracking
- [ ] Enterprise compliance reports (SOC 2, ISO 27001)
- [ ] Slack/Discord bot integration
- [ ] Weekly vulnerability digest email

## License

MIT
