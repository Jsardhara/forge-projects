"""Rendering. The default output is a transition list, not a status dump."""

from typing import List, Optional, Sequence

from .models import CLEAN, ERROR, FINDINGS, UNMEASURABLE, Transition, VerifierResult
from .state import SCHEMA

LABEL_WIDTH = 12


def _label(result: VerifierResult) -> str:
    text = result.status
    if result.exit_code is not None:
        text += f" ({result.exit_code})"
    return text


def render_text(
    results: Sequence[VerifierResult],
    transitions: Sequence[Transition],
    baseline: bool,
    generated_at: str,
    state_path: Optional[str],
) -> str:
    counts: dict = {}
    for res in results:
        counts[res.status] = counts.get(res.status, 0) + 1
    parts = [
        f"{count} {status}" for status, count in sorted(counts.items())
    ]
    lines = [
        f"posture {generated_at}  {len(results)} verifier(s): {', '.join(parts)}"
    ]

    for res in results:
        line = f"  {_label(res):<{LABEL_WIDTH}} {res.name}"
        if res.error:
            line += f"  -- {res.error}"
        lines.append(line)

    lines.append("")
    if baseline:
        lines.append(
            "baseline established — nothing to compare against yet "
            f"({len(results)} verifier(s) recorded{' to ' + state_path if state_path else ''})"
        )
    elif not transitions:
        lines.append("no transitions since the previous run")
    else:
        lines.append(f"{len(transitions)} TRANSITION(S) since the previous run:")
        for item in transitions:
            lines.append("  " + item.describe())

    lines.append(render_verdict(results))
    return "\n".join(lines)


def render_verdict(results: Sequence[VerifierResult]) -> str:
    """One line, worst-first. Exit 2 is never allowed to read as 'fine'."""
    broken = [r.name for r in results if r.status in (UNMEASURABLE, ERROR)]
    if broken:
        return (
            f"verdict: PARTIAL — {len(broken)} verifier(s) could not be measured "
            f"({', '.join(sorted(broken))}); this is not a clean result  EXIT=2"
        )
    findings = [r.name for r in results if r.status == FINDINGS]
    if findings:
        return (
            f"verdict: {len(findings)} verifier(s) need a human "
            f"({', '.join(sorted(findings))})  EXIT=1"
        )
    return "verdict: all clear  EXIT=0"


def render_json(
    results: Sequence[VerifierResult],
    transitions: Sequence[Transition],
    baseline: bool,
    generated_at: str,
    repo_root: str,
    exit_code: int,
) -> str:
    import json

    payload = {
        "schema": SCHEMA,
        "tool": "posture",
        "generated_at": generated_at,
        "repo_root": repo_root,
        "baseline": baseline,
        "exit": exit_code,
        "results": [r.to_dict() for r in results],
        "transitions": [
            {"name": t.name, "field": t.field, "before": t.before, "after": t.after}
            for t in transitions
        ],
    }
    return json.dumps(payload, indent=2, sort_keys=True)
