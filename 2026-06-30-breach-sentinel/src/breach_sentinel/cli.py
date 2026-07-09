"""BreachSentinel command-line interface."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone

from breach_sentinel import __version__
from breach_sentinel.engine import SentinelEngine
from breach_sentinel.models import Identity, Severity
from breach_sentinel.sources import HIBPSource, LocalSource
from breach_sentinel.store import SentinelStore


def _build_sources(args) -> list:
    sources: list = []
    if args.local:
        for path in args.local:
            sources.append(LocalSource(sid=f"local:{os.path.basename(path)}", path=path))
    if args.hibp or (os.environ.get("HIBP_API_KEY") and not args.no_hibp):
        key = os.environ.get("HIBP_API_KEY")
        sources.append(HIBPSource(api_key=key))
    return sources


def _identity_from_args(args) -> Identity:
    iid = args.id or args.label or "ident-1"
    return Identity(
        iid=iid,
        label=args.label or args.id or "identity",
        email=args.email,
        phone=args.phone,
        passport=args.passport,
        ssn=args.ssn,
    )


def cmd_scan(args) -> int:
    sources = _build_sources(args)
    if not sources:
        sys.stderr.write(
            "No sources configured. Use --local <path> or set HIBP_API_KEY env var.\n"
        )
        return 2
    store = SentinelStore(args.db) if args.db else None
    engine = SentinelEngine(sources, store=store)
    ident = _identity_from_args(args)
    result = engine.scan_identity(ident)

    if args.json:
        out = {
            "iid": result.iid,
            "label": result.label,
            "score": result.score.score,
            "severity": result.score.severity.value,
            "record_count": result.score.record_count,
            "critical_types": [t.value for t in result.score.critical_types],
            "alerts": [
                {"severity": a.severity.value, "title": a.title, "body": a.body}
                for a in result.alerts
            ],
            "records": [
                {
                    "source_id": r.source_id,
                    "breach_type": r.breach_type.value,
                    "breach_name": r.breach_name,
                    "breach_date": r.breach_date.isoformat() if r.breach_date else None,
                }
                for r in result.records
            ],
        }
        print(json.dumps(out, indent=2))
    else:
        _print_human(result)

    if result.alerts:
        return 1  # non-zero for CI integration
    return 0


def _print_human(result) -> None:
    print(f"=== BreachSentinel scan: {result.label} ===")
    print(f"Exposure score: {result.score.score}/100  [{result.score.severity.value.upper()}]")
    print(f"Records found: {result.score.record_count}")
    for n in result.score.notes:
        print(f"  - {n}")
    if result.records:
        print("\nBreach records:")
        for r in result.records:
            d = r.breach_date.date().isoformat() if r.breach_date else "unknown"
            print(f"  [{r.breach_type.value}] {r.breach_name} ({d}) via {r.source_id}")
    if result.alerts:
        print("\nALERTS:")
        for a in result.alerts:
            print(f"  [{a.severity.value.upper()}] {a.title}")
            print(f"     {a.body}")


def cmd_report(args) -> int:
    store = SentinelStore(args.db)
    idents = store.list_identities()
    if not idents:
        print("No identities tracked yet. Run `breachsentinel scan` first.")
        return 0
    print("=== Exposure report ===")
    worst: list = []
    for ident in idents:
        recs = []
        for val in ident.search_keys():
            recs.extend(store.breaches_for_identity(val))
        from breach_sentinel.scorer import score_exposure
        score = score_exposure(ident.iid, recs)
        worst.append((score, ident))
        print(f"{ident.label}: {score.score}/100 [{score.severity.value.upper()}] "
              f"({score.record_count} records)")
    worst.sort(key=lambda x: x[0].score, reverse=True)
    if worst:
        top = worst[0][0]
        if top.severity.rank >= Severity.MEDIUM.rank:
            print(f"\nTop risk: {worst[0][1].label} ({top.severity.value})")
    return 0


def cmd_alerts(args) -> int:
    store = SentinelStore(args.db)
    alerts = store.recent_alerts(limit=args.limit)
    if not alerts:
        print("No alerts recorded.")
        return 0
    print(f"=== {len(alerts)} recent alert(s) ===")
    for a in alerts:
        print(f"[{a.severity.value.upper()}] {a.title} ({a.created_at.date().isoformat()})")
        print(f"   {a.body}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="breachsentinel",
        description="Open-source breach exposure monitor (all-stdlib).",
    )
    p.add_argument("--version", action="version", version=f"breachsentinel {__version__}")
    p.add_argument("--db", default="breach_sentinel.db", help="SQLite DB path (default: ./breach_sentinel.db)")
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("scan", help="Scan one identity against configured sources")
    s.add_argument("--label", help="Human-friendly label")
    s.add_argument("--id", help="Stable identity id (iid)")
    s.add_argument("--email")
    s.add_argument("--phone")
    s.add_argument("--passport")
    s.add_argument("--ssn")
    s.add_argument("--local", action="append", help="Path to a local breach JSON/JSONL file (repeatable)")
    s.add_argument("--hibp", action="store_true", help="Use HaveIBeenPwned API (needs HIBP_API_KEY)")
    s.add_argument("--no-hibp", action="store_true", help="Never use HIBP even if HIBP_API_KEY is set")
    s.add_argument("--json", action="store_true", help="Emit JSON instead of human text")
    s.set_defaults(func=cmd_scan)

    r = sub.add_parser("report", help="Summarize exposure across tracked identities")
    r.set_defaults(func=cmd_report)

    a = sub.add_parser("alerts", help="Show recent alerts")
    a.add_argument("--limit", type=int, default=50)
    a.set_defaults(func=cmd_alerts)
    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
