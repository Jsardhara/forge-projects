"""Recommendation engine for tokenaudit.

Turns a CostReport's findings into concrete, prioritized Recommendations with a
rough potential-savings estimate (expressed as a fraction of total tokens, not a
guarantee). The estimates are intentionally conservative and labeled as such.
"""
from __future__ import annotations

from typing import List

from .models import CostReport, Recommendation, WasteFinding

_KIND_REC = {
    "PRE_READ_OVERHEAD": (
        "Trim the init/system context",
        "Much of the pre-tool input is setup context. Shrink the system prompt, drop "
        "unused project docs from context, and use /clear between unrelated tasks so "
        "each run starts lean. This is the single biggest lever -- it is exactly the "
        "33k-vs-7k gap measured between chatty and lean agents.",
    ),
    "REDUNDANT_READS": (
        "Stop re-reading the same files",
        "Use Grep/Glob to locate symbols instead of opening whole files, and delegate "
        "large-file exploration to a subagent so the parent context never ingests the "
        "file twice. One read per file is enough.",
    ),
    "TELEMETRY_OVERHEAD": (
        "Cut repeated tool output",
        "Repeated large tool results (full-file dumps, verbose lint/test output) are "
        "re-fed to the model every turn. Pipe verbose commands through summarizers, "
        "and cache file reads so unchanged content is not re-sent.",
    ),
    "CONTEXT_BLOAT": (
        "Compact context between turns",
        "Context grew much faster than output. Enable periodic compaction or move "
        "state into files/notes the model reads on demand rather than carrying it in "
        "the rolling transcript.",
    ),
}


def _estimate_savings(finding: WasteFinding, total_input: int) -> float | None:
    if total_input <= 0 or finding.wasted_tokens <= 0:
        return None
    share = finding.wasted_tokens / total_input
    # Be conservative: claim at most half of the flagged volume as recoverable.
    return round(min(0.5, share), 3)


def recommendations(report: CostReport) -> List[Recommendation]:
    recs: List[Recommendation] = []
    seen_kinds = {f.kind for f in report.findings}

    for finding in report.findings:
        if finding.kind in _KIND_REC:
            title, detail = _KIND_REC[finding.kind]
            recs.append(
                Recommendation(
                    title=title,
                    detail=detail,
                    potential_savings_pct=_estimate_savings(finding, report.total_input),
                )
            )

    # Generic cost-routing tip only when the absolute bill is material.
    if report.total_cost >= 0.05 and "PRE_READ_OVERHEAD" not in seen_kinds:
        recs.append(
            Recommendation(
                title="Route cheap tasks to small models",
                detail=(
                    "Reserve Opus/Sonnet-class models for hard reasoning; use "
                    "Haiku/Flash for boilerplate edits, formatting, and tests."
                ),
                potential_savings_pct=None,
            )
        )

    if not recs:
        recs.append(
            Recommendation(
                title="No major waste detected",
                detail=(
                    "This session looks efficient -- low pre-read overhead, no "
                    "redundant reads, and no repeated tool output. Keep doing what "
                    "you're doing."
                ),
                potential_savings_pct=None,
            )
        )
    return recs
