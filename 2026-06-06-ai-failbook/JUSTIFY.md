# Project Justification: AI Failbook

## Problem
AI systems fail in predictable, recurring ways — hallucinating facts, refusing benign requests, losing context, generating vulnerable code, and falling for prompt injections. Yet there is no structured, searchable database of these failure modes. Engineers discovering a new AI quirk have nowhere to check if it's a known issue, no standardized taxonomy to categorize it, and no community knowledge base to learn from others' mistakes. The HN thread "What was your 'oh shit' moment with GenAI?" (417 points, 744 comments on June 4, 2026) proves the demand: people desperately want to share and learn from AI failures, but the knowledge is scattered across blog posts, tweets, and comment threads.

## Existing Solutions
- **AI Incident Database (AIID)**: Focuses on real-world harm incidents, not developer-facing failure modes. No CLI, no API, no structured taxonomy for engineering teams.
- **Ad-hoc blog posts**: Not searchable, not structured, not maintained.
- **HN/Reddit threads**: Ephemeral, unstructured, impossible to query.
- **Vendor docs**: Each AI provider documents their own issues in isolation. No cross-model comparison.

None offer: a CLI for quick lookups, a REST API for integration, structured severity/category taxonomy, upvoting to surface common issues, or workaround documentation.

## Proposed Solution
**AI Failbook** — a structured, open-source failure mode database with:
- SQLite backend (zero config, portable)
- Rich CLI with search, filtering, and pretty-printed output
- FastAPI REST API with auto-generated docs
- 12 failure categories (hallucination, prompt injection, tool use, etc.)
- 4 severity levels with color coding
- Upvoting to surface commonly-encountered failures
- Workaround documentation for each failure mode
- 8 real-world seed failures to start

## Impact Criteria
- Database grows to 50+ documented failure modes within first month
- CLI lookup takes <2 seconds for any query
- API serves <50ms per request
- Other Jarmes agents can query it to avoid known AI pitfalls

## Why now
The June 2026 HN conversation explosion (744 comments on AI failures) shows this is a burning need. AI adoption is accelerating (Google paying SpaceX $920M/month for compute), and every team building with AI is encountering these same failures independently. A shared knowledge base saves collective engineering time.
