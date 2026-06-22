"""CLI for PredictGuard — Prediction Market Compliance Platform."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone

from predictguard.models import Trade, Jurisdiction
from predictguard.regulatory import RegulatoryTracker
from predictguard.risk import RiskScorer
from predictguard.audit import AuditTrail
from predictguard.report import ReportGenerator


def _demo_data() -> list[Trade]:
    """Generate demo trade data for CLI demos."""
    now = datetime.now(timezone.utc)
    return [
        Trade(tid="T001", market_id="M001", trader_id="trader_alice", side="buy",
             outcome="Yes", price=0.62, quantity=100, timestamp=now, platform="kalshi",
             jurisdiction=Jurisdiction.CALIFORNIA),
        Trade(tid="T002", market_id="M001", trader_id="trader_alice", side="sell",
             outcome="Yes", price=0.65, quantity=100, timestamp=now, platform="kalshi",
             jurisdiction=Jurisdiction.CALIFORNIA),
        Trade(tid="T003", market_id="M002", trader_id="trader_bob", side="buy",
             outcome="Trump", price=0.45, quantity=500, timestamp=now, platform="polymarket",
             jurisdiction=Jurisdiction.TEXAS),
        Trade(tid="T004", market_id="M003", trader_id="trader_eve", side="buy",
             outcome="Yes", price=0.80, quantity=2000, timestamp=now, platform="kalshi",
             jurisdiction=Jurisdiction.NEVADA),
        Trade(tid="T005", market_id="M001", trader_id="trader_dave", side="buy",
             outcome="No", price=0.38, quantity=50, timestamp=now, platform="crypto_com",
             jurisdiction=Jurisdiction.NEW_YORK),
    ]


def cmd_status(args: argparse.Namespace) -> None:
    """Show regulatory status summary."""
    tracker = RegulatoryTracker()
    summary = tracker.summary()
    print("\n=== PredictGuard Regulatory Status Summary ===\n")
    print(f"{'Status':<20} {'Count':>5}")
    print("-" * 27)
    for status, count in sorted(summary.items()):
        print(f"{status:<20} {count:>5}")
    print()

    restricted = tracker.get_restricted()
    if restricted:
        print(f"Restricted/Blocked Jurisdictions ({len(restricted)}):")
        for r in restricted:
            print(f"  {r.jurisdiction.value}: {r.status} — {r.notes[:80]}")
    print()


def cmd_check(args: argparse.Namespace) -> None:
    """Check if trading is allowed in a jurisdiction."""
    tracker = RegulatoryTracker()
    juris = Jurisdiction(args.jurisdiction.upper())
    allowed, reason = tracker.is_trade_allowed(juris, platform_cftc_compliant=args.cftc)
    status = "✅ ALLOWED" if allowed else "❌ BLOCKED"
    print(f"\n{args.jurisdiction.upper()}: {status}")
    print(f"  Reason: {reason}")
    print()


def cmd_risk(args: argparse.Namespace) -> None:
    """Run risk analysis on demo data."""
    trades = _demo_data()
    scorer = RiskScorer()
    scorer.add_trades(trades)

    threshold = args.threshold
    print(f"\n=== PredictGuard Risk Analysis (threshold={threshold}) ===\n")

    print("--- Trader Risk ---")
    assessments = scorer.score_all_traders()
    for a in assessments:
        flag = "🚩" if a.risk_score >= threshold else "  "
        print(f"  {flag} {a.target_id}: {a.risk_level.value} ({a.risk_score:.2f}) — {len(a.flags)} flags")
        for f in a.flags:
            print(f"      • {f}")

    print("\n--- Market Risk ---")
    market_assessments = scorer.score_all_markets()
    for a in market_assessments:
        flag = "🚩" if a.risk_score >= threshold else "  "
        print(f"  {flag} {a.target_id}: {a.risk_level.value} ({a.risk_score:.2f}) — {len(a.flags)} flags")
        for f in a.flags:
            print(f"      • {f}")
    print()


def cmd_report(args: argparse.Namespace) -> None:
    """Generate a compliance report from demo data."""
    trades = _demo_data()
    now = datetime.now(timezone.utc)
    scorer = RiskScorer()
    scorer.add_trades(trades)
    risk_assessments = scorer.score_all_traders() + scorer.score_all_markets()

    gen = ReportGenerator()
    report = gen.generate(
        trades=trades,
        risk_assessments=risk_assessments,
        period_start=now,
        period_end=now,
        jurisdiction=None,
    )

    if args.format == "json":
        data = {
            "id": report.rid,
            "generated_at": report.generated_at.isoformat(),
            "total_trades": report.total_trades,
            "total_volume": report.total_volume,
            "flagged_trades": report.flagged_trades,
            "compliance_score": report.compliance_score,
            "findings": report.findings,
            "recommendations": report.recommendations,
        }
        print(json.dumps(data, indent=2))
    else:
        print(ReportGenerator.format_report(report))


def cmd_audit(args: argparse.Namespace) -> None:
    """Generate and export audit trail."""
    trail = AuditTrail()
    now = datetime.now(timezone.utc)

    trail.log("system", "predictguard", "Audit trail initialized")
    trail.log("compliance_check", "scheduler", "Daily compliance check completed")
    trades = _demo_data()
    for t in trades:
        trail.log("trade", t.trader_id, f"Trade {t.tid}: {t.side} {t.outcome} @ {t.price} on {t.platform}",
                  metadata={"market_id": t.market_id, "quantity": t.quantity})

    valid, failed = trail.verify_integrity()
    print(f"\nAudit Trail: {trail.entry_count} entries")
    print(f"Integrity check: {'PASS' if valid else 'FAIL'}")
    if failed:
        print(f"Failed entries: {failed}")

    output = trail.export_csv() if args.format == "csv" else trail.export_json()
    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"Exported to {args.output}")
    else:
        print(f"\n{output}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="predictguard",
        description="PredictGuard — Prediction Market Compliance Platform",
    )
    sub = parser.add_subparsers(dest="command", help="Available commands")

    # status
    sub.add_parser("status", help="Show regulatory status summary")

    # check
    check_p = sub.add_parser("check", help="Check if trading is allowed in a jurisdiction")
    check_p.add_argument("jurisdiction", help="Jurisdiction code (e.g., CA, NV, TX, UK)")
    check_p.add_argument("--cftc", action="store_true", help="Platform is CFTC-compliant")

    # risk
    risk_p = sub.add_parser("risk", help="Run risk analysis")
    risk_p.add_argument("--threshold", type=float, default=0.5, help="Risk threshold (0.0-1.0)")

    # report
    report_p = sub.add_parser("report", help="Generate compliance report")
    report_p.add_argument("--format", choices=["text", "json"], default="text", help="Output format")

    # audit
    audit_p = sub.add_parser("audit", help="Generate audit trail")
    audit_p.add_argument("--format", choices=["json", "csv"], default="json", help="Output format")
    audit_p.add_argument("--output", help="Output file path")

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        sys.exit(0)

    cmds = {
        "status": cmd_status,
        "check": cmd_check,
        "risk": cmd_risk,
        "report": cmd_report,
        "audit": cmd_audit,
    }
    cmds[args.command](args)


if __name__ == "__main__":
    main()
