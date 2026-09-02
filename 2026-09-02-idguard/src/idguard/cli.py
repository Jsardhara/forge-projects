"""idguard CLI: scan a breach dump for leaked identity assets and emit severity +
exit gate; generate breach-notification compliance triage."""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from typing import Dict, List

from idguard.engine import (
    RecordResult,
    ScanTotals,
    aggregate,
    exit_code,
    scan_record,
)
from idguard.notify import build_notification_plan, lookup_state


def _load_records(path: str) -> List[Dict[str, object]]:
    """Load records from CSV, JSON, or JSONL. '-' reads stdin."""
    raw = sys.stdin.read() if path == "-" else open(path, "r", encoding="utf-8", errors="replace").read()
    low = path.lower()
    if low.endswith(".csv") or (path == "-"):
        try:
            reader = csv.DictReader(io.StringIO(raw))
            return [dict(row) for row in reader if any((v or "").strip() for v in row.values())]
        except Exception as exc:  # pragma: no cover - fallback
            raise SystemExit(f"error: could not parse CSV: {exc}")
    if low.endswith(".jsonl"):
        out = []
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if isinstance(obj, dict):
                out.append(obj)
        return out
    # JSON
    data = json.loads(raw)
    if isinstance(data, list):
        return [r for r in data if isinstance(r, dict)]
    if isinstance(data, dict):
        for key in ("records", "data", "breaches", "rows", "entries"):
            if isinstance(data.get(key), list):
                return [r for r in data[key] if isinstance(r, dict)]
        # single object -> one record
        return [data]
    return []


def _render_totals(t: ScanTotals) -> str:
    sev = " / ".join(f"{s}={t.count_by_severity.get(s, 0)}" for s in ("CRIT", "HIGH", "MEDIUM", "LOW"))
    return (
        f"scanned={t.scanned} | {sev} | exposed_valid_ssn={t.exposed_ssns} | "
        f"dl_with_hint={t.exposed_dls} | states_hit={','.join(sorted(t.states_hit)) or 'none'}"
    )


def _cmd_scan(args: argparse.Namespace) -> int:
    records = _load_records(args.file)
    if not records:
        print("error: no records loaded", file=sys.stderr)
        return 2
    results: List[RecordResult] = []
    for i, rec in enumerate(records):
        results.append(scan_record(i, rec))
    totals = aggregate(results, total_scanned=len(records))
    efmt = dict if args.json else str
    if args.json:
        payload = {
            "scanned": totals.scanned,
            "severity_counts": totals.count_by_severity,
            "exposed_ssn": totals.exposed_ssns,
            "exposed_dl": totals.exposed_dls,
            "states_hit": sorted(totals.states_hit),
            "critical_records": totals.critical_ids,
            "max_severity": totals.max_severity,
        }
        print(json.dumps(payload, separators=(",", ":")))
    else:
        for r in results:
            det = ", ".join(str(f) for f in r.findings) or "-"
            print(f"#{r.index} {r.severity:6s} {det}")
        print(_render_totals(totals))
    code = exit_code(totals, warn_threshold=args.threshold)
    return code


def _cmd_notify(args: argparse.Namespace) -> int:
    states = [s.strip().upper() for s in (args.states or "").split(",") if s.strip()]
    if states:
        unknown = [s for s in states if not _valid_state(s)]
        if unknown:
            print(f"error: unknown state code(s): {','.join(unknown)}", file=sys.stderr)
            return 2
    plan = build_notification_plan(
        state_codes=states or None,
        affected_subscribers=args.subscribers,
        affected_residents=args.residents,
        evidence_summary=args.summary or "",
    )
    print(plan)
    return 0


def _valid_state(code: str) -> bool:
    try:
        lookup_state(code)
        return True
    except KeyError:
        return False


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="idguard", description="Identity-exposure & breach-notification screener")
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("scan", help="scan a breach dump (csv/json/jsonl)")
    s.add_argument("file", help="path to dump; '-' for stdin")
    s.add_argument("--json", action="store_true", help="machine-readable output")
    s.add_argument("--threshold", type=int, default=1, help="HIGH records that trigger exit 1")
    s.set_defaults(func=_cmd_scan)

    n = sub.add_parser("notify", help="emit 50-state breach-notification triage")
    n.add_argument("--states", default="", help="comma-separated state codes (default: all)")
    n.add_argument("--subscribers", type=int, default=0, help="affected subscriber count")
    n.add_argument("--residents", type=int, default=0, help="affected residents in covered states")
    n.add_argument("--summary", default="", help="one-line evidence scope summary")
    n.set_defaults(func=_cmd_notify)

    return p


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())