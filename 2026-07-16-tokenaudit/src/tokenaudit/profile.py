"""Analysis engine for tokenaudit.

Turns a parsed Session into a PhaseBreakdown, a list of FileReads, and a list of
WasteFindings. This is the diagnostic core that distinguishes tokenaudit from the
live spend-tracking tools (ai-cost-guard, ai-token-proxy, model-router, pricewatch):
it explains *where* tokens went and *why*, not just *how many*.
"""
from __future__ import annotations

import hashlib
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from .models import FileRead, Message, PhaseBreakdown, Session, Usage, WasteFinding
from .pricing import DEFAULT_PRICING, cost_for

# Thresholds (tunable). Based on the Lens signal that Claude Code can spend ~33k
# input tokens before its first tool call while OpenCode spends ~7k.
PREREAD_HIGH = 8000
PREREAD_WARN = 3000
REDUNDANT_WARN = 1000
REDUNDANT_HIGH = 5000
TELEMETRY_MIN_REPEATS = 3
TELEMETRY_MIN_CHARS = 500
CONTEXT_BLOAT_INPUT = 100_000
CONTEXT_BLOAT_RATIO = 50


def dominant_model(session: Session) -> Optional[str]:
    counts: Dict[str, int] = defaultdict(int)
    for m in session.messages:
        if m.model:
            counts[m.model] += 1
    if not counts:
        return None
    return max(counts.items(), key=lambda kv: kv[1])[0]


def phase_breakdown(session: Session) -> PhaseBreakdown:
    """Classify every input/output token by phase.

    preread_input  = input tokens of all messages up to AND INCLUDING the first
                     message that calls a tool (the "setup"/context before work).
    tool_result_input = input tokens from messages carrying tool results.
    other_input    = remaining input (follow-up instructions, summaries).
    generation_output = all output tokens.
    """
    first_tool_idx = None
    for i, m in enumerate(session.messages):
        if m.has_tool_use:
            first_tool_idx = i
            break

    preread = tool_result = other = 0
    for i, m in enumerate(session.messages):
        inp = m.usage.input_tokens
        if m.has_tool_result:
            tool_result += inp
        elif first_tool_idx is None or i <= first_tool_idx:
            preread += inp
        else:
            other += inp
    generation = sum(m.usage.output_tokens for m in session.messages)
    return PhaseBreakdown(
        preread_input=preread,
        tool_result_input=tool_result,
        other_input=other,
        generation_output=generation,
    )


def file_reads(session: Session) -> List[FileRead]:
    """Aggregate file reads across the session, estimating token cost per file."""
    agg: Dict[str, List[int]] = defaultdict(list)
    for m in session.messages:
        paths = m.file_reads
        if not paths:
            continue
        per = m.usage.input_tokens / len(paths) if m.usage.input_tokens else 0
        for p in paths:
            agg[p].append(int(per))
    out: List[FileRead] = []
    for path, toks in agg.items():
        out.append(
            FileRead(
                path=path,
                read_count=len(toks),
                est_input_tokens=sum(toks),
            )
        )
    out.sort(key=lambda fr: (fr.read_count, fr.est_input_tokens), reverse=True)
    return out


def _tool_result_texts(message: Message) -> List[str]:
    """Extract plain-text tool results from a user message's content."""
    texts: List[str] = []
    blocks = message.content if isinstance(message.content, list) else []
    for b in blocks:
        if not isinstance(b, dict):
            continue
        if b.get("type") != "tool_result":
            continue
        c = b.get("content")
        if isinstance(c, str):
            texts.append(c)
        elif isinstance(c, list):
            for part in c:
                if isinstance(part, dict) and isinstance(part.get("text"), str):
                    texts.append(part["text"])
                elif isinstance(part, str):
                    texts.append(part)
    return texts


def waste_findings(session: Session,
                   pricing_table: Optional[Dict] = None) -> List[WasteFinding]:
    table = pricing_table or DEFAULT_PRICING
    model = dominant_model(session)
    phase = phase_breakdown(session)
    findings: List[WasteFinding] = []

    # 1) Pre-read overhead
    if phase.preread_input >= PREREAD_WARN:
        sev = "HIGH" if phase.preread_input >= PREREAD_HIGH else "WARN"
        cost = cost_for(model, phase.preread_input, 0, table)
        findings.append(
            WasteFinding(
                kind="PRE_READ_OVERHEAD",
                severity=sev,
                detail=(
                    f"{phase.preread_input:,} input tokens loaded before the first "
                    f"tool call (setup/context). This is the 'reads the prompt before "
                    f"working' overhead; capping system context or clearing between "
                    f"tasks can recover much of it."
                ),
                wasted_tokens=phase.preread_input,
                wasted_cost=cost,
            )
        )

    # 2) Redundant file reads
    redundant_tokens = 0
    redundant_files = 0
    for fr in file_reads(session):
        if fr.read_count > 1:
            redundant_files += 1
            per = fr.est_input_tokens / fr.read_count if fr.read_count else 0
            redundant_tokens += int(per * (fr.read_count - 1))
    if redundant_tokens >= REDUNDANT_WARN:
        sev = "HIGH" if redundant_tokens >= REDUNDANT_HIGH else "WARN"
        cost = cost_for(model, redundant_tokens, 0, table)
        findings.append(
            WasteFinding(
                kind="REDUNDANT_READS",
                severity=sev,
                detail=(
                    f"{redundant_files} file(s) read more than once; an estimated "
                    f"{redundant_tokens:,} input tokens were re-loaded unnecessarily. "
                    f"Prefer Grep/Glob over repeated full-file Read, and isolate large "
                    f"reads in subagents."
                ),
                wasted_tokens=redundant_tokens,
                wasted_cost=cost,
            )
        )

    # 3) Telemetry / repeated large tool output
    seen: Dict[str, List[int]] = defaultdict(list)
    for m in session.messages:
        if not m.has_tool_result:
            continue
        for t in _tool_result_texts(m):
            if len(t) < TELEMETRY_MIN_CHARS:
                continue
            h = hashlib.sha1(t.encode("utf-8", "replace")).hexdigest()[:16]
            seen[h].append(m.usage.input_tokens)
    telemetry_tokens = 0
    telemetry_hits = 0
    for h, toks in seen.items():
        if len(toks) >= TELEMETRY_MIN_REPEATS:
            telemetry_hits += 1
            # first occurrence is "necessary"; the rest are waste
            telemetry_tokens += sum(toks[1:])
    if telemetry_tokens > 0:
        sev = "HIGH" if telemetry_tokens >= REDUNDANT_HIGH else "WARN"
        cost = cost_for(model, telemetry_tokens, 0, table)
        findings.append(
            WasteFinding(
                kind="TELEMETRY_OVERHEAD",
                severity=sev,
                detail=(
                    f"{telemetry_hits} distinct large tool output(s) were returned "
                    f"{TELEMETRY_MIN_REPEATS}+ times (est. {telemetry_tokens:,} repeated "
                    f"input tokens). Repeated full-file dumps or verbose lint/command "
                    f"output inflate context every turn."
                ),
                wasted_tokens=telemetry_tokens,
                wasted_cost=cost,
            )
        )

    # 4) Context bloat (informational)
    total_input = phase.total_input
    ratio = (total_input / phase.generation_output) if phase.generation_output else float("inf")
    if total_input >= CONTEXT_BLOAT_INPUT and ratio >= CONTEXT_BLOAT_RATIO:
        findings.append(
            WasteFinding(
                kind="CONTEXT_BLOAT",
                severity="INFO",
                detail=(
                    f"Total input {total_input:,} tokens with input/output ratio "
                    f"{ratio:.0f}x. Context grew far faster than output -- a sign of "
                    f"monotonic context accumulation across the session."
                ),
                wasted_tokens=0,
                wasted_cost=0.0,
            )
        )

    return findings
