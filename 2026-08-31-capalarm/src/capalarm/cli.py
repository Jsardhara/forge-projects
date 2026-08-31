"""Command-line interface for capalarm."""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from typing import IO, Optional, TextIO

from capalarm.engine import aggregate, evaluate, exit_code_for, overall_verdict
from capalarm.models import Finding, Plan, UsageSample, Severity
from capalarm.plans import DEFAULT_PLANS, plans_for_provider


def _parse_ts(raw: str) -> datetime:
    """Parse an ISO-8601 timestamp, defaulting naive input to UTC."""
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:  # pragma: no cover - argparse robustness
        raise SystemExit(f"capalarm: invalid timestamp {raw!r}: {exc}")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _read_records(fh: TextIO, fmt: str) -> list[dict]:
    if fmt == "csv":
        reader = csv.DictReader(fh)
        return list(reader)
    # JSON: either a list of records or {records: [...]}
    data = json.load(fh)
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and isinstance(data.get("records"), list):
        return data["records"]
    raise ValueError("JSON input must be a list or {'records': [...]}")


def _samples_from_records(records: list[dict]) -> list[UsageSample]:
    samples: list[UsageSample] = []
    for r in records:
        provider = (r.get("provider") or r.get("model") or "").strip()
        if not provider:
            raise ValueError(f"record missing 'provider': {r}")
        ts = _parse_ts((r.get("timestamp") or r.get("ts")).strip())
        try:
            tokens = int(r.get("tokens") or r.get("usage_tokens") or r.get("token_usage") or 0)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"record missing numeric 'tokens': {r}") from exc
        samples.append(UsageSample(provider=provider, timestamp=ts, tokens=tokens))
    return samples


def _render_text(findings: list[Finding], verdict: str) -> str:
    out = [f"capalarm verdict: {verdict}", ""]
    for f in findings:
        out.append(f"[{f.rule}] {f.severity}  {f.message}")
    out.append("")
    return "\n".join(out)


def _render_json(findings: list[Finding], verdict: str) -> str:
    payload = {
        "verdict": verdict,
        "findings": [
            {"rule": f.rule, "severity": f.severity, "message": f.message}
            for f in findings
        ],
    }
    return json.dumps(payload, indent=2)


def _resolve_plan(provider: str, plan_id: Optional[str]) -> Optional[Plan]:
    if plan_id:
        for p in DEFAULT_PLANS:
            if p.id == plan_id:
                return p
        return None
    return plans_for_provider(provider)[0] if plans_for_provider(provider) else None


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="capalarm",
        description="Subscription AI plan-cap compliance & headroom forecaster.",
    )
    p.add_argument("input", nargs="?", help="path to usage CSV/JSON (default: stdin)")
    p.add_argument("--format", choices=["csv", "json", "auto"], default="auto")
    p.add_argument("--provider", help="limit evaluation to one provider slug")
    p.add_argument("--plan", help="force a specific default plan id (e.g. anthropic-claude-max)")
    p.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    p.add_argument("--claude-max", action="store_true", help="shorthand: treat all as Anthropic Claude Max (Pro) plan")
    return p


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    # Determine format when not forced.
    fmt = args.format
    if fmt == "auto":
        if args.input and args.input.lower().endswith(".json"):
            fmt = "json"
        elif args.input and args.input.lower().endswith((".csv", ".tsv")):
            fmt = "csv"
        else:
            fmt = "json"

    fh: IO[str]
    try:
        fh = open(args.input, "r", encoding="utf-8") if args.input else sys.stdin
    except OSError as exc:
        print(f"capalarm: cannot open {args.input}: {exc}", file=sys.stderr)
        return 2

    try:
        records = _read_records(fh, fmt)
        samples = _samples_from_records(records)
    except (ValueError, csv.Error, json.JSONDecodeError) as exc:
        print(f"capalarm: parse error: {exc}", file=sys.stderr)
        if fh is not sys.stdin:
            fh.close()
        return 2
    finally:
        if fh is not sys.stdin:
            fh.close()

    if args.claude_max:
        # Force every provider onto the Claude Max (Pro) plan for a focused check.
        plan = next(p for p in DEFAULT_PLANS if p.id == "anthropic-claude-max")
        effective_plans = {s.provider: plan for s in samples}
    else:
        effective_plans = {
            s.provider: _resolve_plan(s.provider, args.plan) for s in samples
        }

    by_provider = aggregate(samples)
    all_findings: list[Finding] = []
    for provider, usage in by_provider.items():
        if args.provider and provider != args.provider:
            continue
        plan = effective_plans.get(provider)
        findings, _forecast = evaluate(provider, usage, plan)
        all_findings.extend(findings)

    verdict = overall_verdict(all_findings)
    if args.json:
        print(_render_json(all_findings, verdict))
    else:
        print(_render_text(all_findings, verdict))
    return exit_code_for(verdict)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())