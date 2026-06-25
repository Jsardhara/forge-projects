# Project Justification: PRBouncer

**Problem:** Open source maintainers are drowning in AI-slop PRs. Greptile reported that PR spam today looks like email spam in the early 2000s (HN #20, 223 pts). GitHub PR volume jumped 29% YoY in 2026, with estimates that only 1 in 10 AI-generated PRs is legitimate. Existing tools (anti-slop, github/ai-moderator) are TypeScript GitHub Actions — not reusable Python libraries. Maintainers using Python-based workflows (PyGitHub, etc.) have no standalone heuristic engine to call programmatically.

**User:** Open source maintainers and platform trust & safety teams who need a Python library (not a Node.js GitHub Action) to detect, score, and triage spam/low-quality PRs.

**Why existing solutions are inadequate:**
- `anti-slop` (688★) — TypeScript GitHub Action only. No Python library, no CLI-only mode, no programmatic scoring API.
- `github/ai-moderator` (199★) — TypeScript, GitHub-specific, requires LLM calls for classification (costly, slow, non-deterministic).
- `pr-triage` — AI-powered but relies on external LLM; no pure-heuristic fallback for deterministic scoring.
- None offer a multi-signal heuristic engine (account age + PR patterns + diff analysis + content markers) that runs without an LLM.

**Success metric:** A PR receives a spam probability score (0.0–1.0) in <50ms without any external API calls, with adjustable thresholds and explainable signals.
