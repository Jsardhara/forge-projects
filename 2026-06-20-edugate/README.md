# EduGate — AI Access Gateway for Schools

**Age-gated AI access control with teacher oversight and compliance reporting.**

EduGate is an open-source gateway that enforces school AI usage policies at the network level. It was built in response to Norway's August 2026 ban on generative AI for elementary students (grades 1-7, ages 6-13), but is designed to be configurable for any regulatory framework.

## Why EduGate

- **Norway banned AI in elementary schools** (Reuters, June 19, 2026, HN 477pts)
- **No open-source tool exists** for enforcing age-based AI access policies
- Commercial K-12 AI platforms (LittleLit, SchoolAI, Teachfloor) are proprietary SaaS — they provide curriculum, not access control
- Schools need a **technical enforcement layer**, not just policy documents

## Features

- **Policy Engine**: Grade-band-based access control (elementary / lower secondary / upper secondary)
- **Teacher Override**: Teachers can grant supervised access to specific tools
- **Daily Limits**: Configurable per-student daily request caps
- **Audit Logging**: Append-only event log with SHA-256 hashed IPs for privacy
- **Compliance Reports**: Auto-generated Norway 2026 compliance reports
- **CLI**: `edugate demo`, `edugate policy`, `edugate audit`, `edugate compliance`
- **Server-Rendered Dashboard**: FastAPI + Jinja2, zero Node.js dependency

## Quick Start

```bash
pip install -e ".[dev]"
edugate demo
```

## Policy Model

Norway's August 2026 regulations (loaded via `load_norway_defaults()`):

| Grade Band | Ages | Default | Notes |
|---|---|---|---|
| Elementary (1-7) | 6-13 | DENY | Near-total ban |
| Lower Secondary (8-10) | 14-16 | REQUIRE_SUPERVISION | Teacher must be present |
| Upper Secondary (11-13) | 17-19 | ALLOW | Learn appropriate use |

## Architecture

```
src/edugate/
├── __init__.py     # Public API exports
├── policy.py       # PolicyEngine, Student, Teacher, AccessPolicy
├── audit.py        # AuditLogger, AuditEvent
├── compliance.py   # Norway 2026 compliance report generator
├── gateway.py      # Gateway facade (policy + audit + compliance)
└── cli.py          # CLI commands
```

## Compliance

EduGate generates compliance reports checking:

- **POL-001**: Policies configured for all grade bands
- **ELEM-001**: Elementary AI ban enforced (≥95% denial rate)
- **LOWSEC-001**: Lower secondary AI use supervised (≥90% supervision rate)
- **AUDIT-001**: Audit trail maintained

## License

MIT
