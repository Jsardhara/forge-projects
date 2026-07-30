# vibecraft — AI-Assisted Code Craftsmanship Auditor

**Detect vibe-coding anti-patterns, measure code quality, enforce CI gates.**

`vibecraft` statically analyzes Python source code and returns a craftsmanship score (0–100) with specific findings about documentation coverage, error handling, complexity, naming consistency, and magic values — the hallmark patterns of AI-assisted "vibe-coded" output.

---

## Quick Start

```bash
pip install vibecraft

# Analyze a file
vibecraft analyze myapp/utils.py

# CI gate — exit 1 if score < 70
vibecraft check myapp/utils.py --threshold 70

# JSON output (for automation)
vibecraft analyze myapp/utils.py --json
```

---

## What It Detects

| Pattern | Code | Severity | Description |
|---------|------|----------|-------------|
| Bare `except:` | `bare_except` | WARNING | Catches all exceptions; be explicit |
| `except Exception: pass` | `except_exception_pass` | CRITICAL | Silently swallows errors |
| Empty except handler | `except_pass` | WARNING | Errors are silently ignored |
| Missing docstring | `missing_docstring` | INFO | Public function/class has no docstring |
| Empty docstring | `empty_docstring` | WARNING | Trivial or placeholder docstring |
| Deep nesting | `deep_nesting` | WARNING | `if`/`for`/`while` depth > 3 |
| Long function | `long_function` | WARNING | Function exceeds 50 lines |
| Magic string | `magic_string` | INFO | Long string literal not in constants |
| Magic number | `magic_number` | INFO | Numeric literal should be named constant |
| Hardcoded URL | `hardcode_url` | INFO | Inline URL should be configurable |
| Hardcoded path | `hardcode_path` | INFO | Absolute path should use `Path`/`os.path` |
| `print()` in code | `print_in_code` | INFO | Use `logging` instead |
| Incomplete TODO | `incomplete_todo` | INFO | TODO without actionable description |
| Mixed naming | `inconsistent_naming` | INFO | snake_case + camelCase + PascalCase mixed |

---

## Craftsmanship Score

The 0–100 score is a weighted composite of four subscores:

- **Documentation coverage** (20%): % of functions/classes with real docstrings
- **Error handling** (25%): presence of bare/empty excepts reduces this
- **Complexity** (25%): nesting depth and function length penalties
- **Naming consistency** (15%): single convention preferred
- **Magic values** (15%): penalty per magic string/number

### Grade bands

| Score | Grade | Band |
|-------|-------|------|
| 90–100 | A | excellent |
| 80–89 | B | good |
| 70–79 | C | fair |
| 50–69 | D | poor |
| 0–49 | F | failing |

---

## CLI Commands

### `vibecraft analyze <file>`
Print a human-readable craftsmanship report.

### `vibecraft check <file> [--threshold N]`
CI gate mode. Exits 0 if score >= threshold, 1 otherwise. Use in CI pipelines:
```yaml
# .github/workflows/ci.yml
- name: Craftsmanship check
  run: vibecraft check src/ --threshold 75
```

---

## Python API

```python
from vibecraft import score_craftsmanship

report = score_craftsmanship(open("myapp.py").read(), "myapp.py")
print(f"Score: {report.score}  Grade: {report.grade}")
for finding in report.findings:
    print(f"  [{finding.severity.value}] L{finding.line}: {finding.message}")
```

---

## Installation

```bash
pip install .
```

Requires Python 3.11+.
