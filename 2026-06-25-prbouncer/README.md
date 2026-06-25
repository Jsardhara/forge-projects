# PRBouncer

**PR spam detection engine for open source maintainers.**

Multi-signal heuristic scoring — no LLM calls, no external APIs, no GitHub Actions. Just a Python library that scores PRs for spam probability in <50ms.

## The Problem

PR spam in open source is the new email spam. Greptile reports PR volume jumped 29% YoY on GitHub, with only ~1 in 10 AI-generated PRs being legitimate. Maintainers are drowning.

## How It Works

PRBouncer evaluates 9 independent spam signals and combines them with configurable weights:

| Signal | Weight | Description |
|--------|--------|-------------|
| `new_account` | 0.20 | Account age (<7d = suspicious, <1d = highly suspicious) |
| `ai_slop_markers` | 0.25 | AI-generated phrases in PR body ("I have analyzed the codebase…") |
| `no_linked_issue` | 0.15 | No linked issue or manual #ref in title/body |
| `rapid_fire` | 0.15 | Many recent PRs from same author |
| `generic_title` | 0.12 | Vague or pattern-matched titles ("Update code", "Fix") |
| `large_diff` | 0.10 | Disproportionately large changes for account age |
| `account_pattern` | 0.10 | Bot-like username patterns, no bio/pic/followers |
| `suspicious_files` | 0.08 | Only touching docs/config files (for new accounts) |
| `low_engagement` | 0.05 | Zero comments/reviews on PR from new account |

Each signal returns a raw score (0.0–1.0). The engine computes a weighted probability and classifies:
- **LEGIT** (p < 0.25)
- **SUSPICIOUS** (0.25 ≤ p ≤ 0.65)
- **SPAM** (p > 0.65)

## Quick Start

```python
from prbouncer import SpamEngine, PullRequest, AuthorProfile

author = AuthorProfile(
    username="newbie-12345",
    account_age_days=2,
    followers=0,
    has_bio=False,
    has_profile_pic=False,
)

pr = PullRequest(
    pr_number=42,
    title="Update code",
    body="I have analyzed the codebase and this PR improves the codebase.",
    author=author,
    linked_issues=0,
    file_paths=("README.md",),
)

engine = SpamEngine()
verdict = engine.evaluate(pr, recent_pr_count=8)

print(verdict.classification)   # "SPAM"
print(verdict.spam_probability) # e.g., 0.782
print(verdict.explain)          # Full multi-line explanation
```

## CLI

```bash
# Analyze a single PR
prbouncer analyze --pr 42 --title "Fix bug" --body "..." --author user --account-age 5

# With JSON output
prbouncer analyze --pr 42 --title "Update code" --author bot-123 --account-age 0 --json

# Batch from stdin
echo '[{"pr_number": 1, "title": "Fix", ...}]' | prbouncer batch

# Show thresholds
prbouncer thresholds
```

## Design Decisions

- **Zero dependencies** — stdlib only. No PyGitHub, no LLM, no network calls.
- **Deterministic** — same input always produces same output. No randomness.
- **Fast** — scoring is pure Python with no I/O. Sub-millisecond per PR.
- **Explainable** — every signal includes human-readable evidence strings.
- **Configurable thresholds** — LEGIT/SPAM boundaries are adjustable.

## Installation

```bash
pip install prbouncer
```

## License

MIT
