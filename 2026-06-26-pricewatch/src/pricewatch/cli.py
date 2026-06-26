"""CLI interface for PriceWatch."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from typing import Optional

from . import __version__
from .alerts import generate_alerts, generate_price_war_alert
from .detector import detect_changes, detect_price_wars
from .models import AlertSeverity, PriceSnapshot, Tier
from .providers import current_snapshot
from .ranking import compare_models, rank_all_tiers, rank_by_tier
from .store import PriceStore
from .trends import compute_trends


def _json_snapshot(snap: PriceSnapshot) -> dict:
    return {
        "timestamp": snap.timestamp.isoformat(),
        "models": [
            {
                "provider": e.provider.value,
                "model_id": e.model_id,
                "tier": e.tier.value,
                "input_per_mtok": e.input_price_per_mtok,
                "output_per_mtok": e.output_price_per_mtok,
                "context_window": e.context_window,
                "blended": round(e.blended_price, 4),
            }
            for e in snap.entries
        ],
    }


def cmd_scan(args: argparse.Namespace) -> None:
    """Scan all providers for current prices."""
    snap = current_snapshot()

    if args.store:
        store = PriceStore(args.store)
        store.save_snapshot(snap)
        store.close()

    if args.json:
        print(json.dumps(_json_snapshot(snap), indent=2))
        return

    # Rich table output
    try:
        from rich.console import Console
        from rich.table import Table

        console = Console()
        table = Table(title=f"LLM Pricing — {snap.timestamp.strftime('%Y-%m-%d %H:%M UTC')}")
        table.add_column("Provider", style="cyan")
        table.add_column("Model", style="bold")
        table.add_column("Tier", style="dim")
        table.add_column("Input/Mtok", justify="right")
        table.add_column("Output/Mtok", justify="right")
        table.add_column("Blended", justify="right", style="green")
        table.add_column("Context", justify="right", style="dim")

        for e in sorted(snap.entries, key=lambda x: (x.tier.value, x.blended_price)):
            table.add_row(
                e.provider.value,
                e.model_id,
                e.tier.value,
                f"${e.input_price_per_mtok:.3f}",
                f"${e.output_price_per_mtok:.3f}",
                f"${e.blended_price:.3f}",
                f"{e.context_window:,}",
            )

        console.print(table)
    except ImportError:
        # Fallback without rich
        print(f"LLM Pricing — {snap.timestamp.strftime('%Y-%m-%d %H:%M UTC')}")
        print(f"{'Provider':<12} {'Model':<28} {'Tier':<12} {'In/Mtok':>10} {'Out/Mtok':>10} {'Blended':>10} {'Ctx':>10}")
        print("-" * 92)
        for e in sorted(snap.entries, key=lambda x: (x.tier.value, x.blended_price)):
            print(
                f"{e.provider.value:<12} {e.model_id:<28} {e.tier.value:<12} "
                f"${e.input_price_per_mtok:>8.3f} ${e.output_price_per_mtok:>8.3f} "
                f"${e.blended_price:>8.3f} {e.context_window:>10,}"
            )


def cmd_compare(args: argparse.Namespace) -> None:
    """Compare models across providers."""
    snap = current_snapshot()

    if args.models:
        rankings = compare_models(snap, args.models.split(","))
    elif args.tier:
        tier = Tier(args.tier)
        rankings = rank_by_tier(snap, tier, by=args.sort or "blended")
    else:
        all_rankings = rank_all_tiers(snap, by=args.sort or "blended")
        # Flatten for display
        rankings = []
        for tier_rankings in all_rankings.values():
            rankings.extend(tier_rankings)

    if args.json:
        data = [
            {
                "rank": r.rank,
                "provider": r.pricing.provider.value,
                "model_id": r.pricing.model_id,
                "tier": r.tier.value,
                "blended": round(r.score, 4),
                "input": r.pricing.input_price_per_mtok,
                "output": r.pricing.output_price_per_mtok,
                "context": r.pricing.context_window,
            }
            for r in rankings
        ]
        print(json.dumps(data, indent=2))
        return

    try:
        from rich.console import Console
        from rich.table import Table

        console = Console()
        table = Table(title="Model Cost Ranking")
        table.add_column("#", justify="right", style="bold")
        table.add_column("Provider", style="cyan")
        table.add_column("Model", style="bold")
        table.add_column("Tier", style="dim")
        table.add_column("Blended/Mtok", justify="right", style="green")
        table.add_column("Context", justify="right", style="dim")

        for r in rankings:
            table.add_row(
                str(r.rank),
                r.pricing.provider.value,
                r.pricing.model_id,
                r.tier.value,
                f"${r.score:.3f}",
                f"{r.pricing.context_window:,}",
            )

        console.print(table)
    except ImportError:
        for r in rankings:
            print(f"#{r.rank} {r.pricing.provider.value}/{r.pricing.model_id} [{r.tier.value}] ${r.score:.3f}/Mtok")


def cmd_alerts(args: argparse.Namespace) -> None:
    """Show price alerts from stored snapshots."""
    store = PriceStore(args.store)
    current = store.latest_snapshot()
    previous = store.previous_snapshot()
    store.close()

    if current is None or previous is None:
        print("Need at least 2 snapshots to detect changes. Run 'pricewatch scan --store <db>' first.", file=sys.stderr)
        return

    deltas = detect_changes(current, previous)
    alerts = generate_alerts(deltas)

    # Check for price wars
    wars = detect_price_wars(deltas)
    for war in wars:
        alerts.append(generate_price_war_alert(war))

    # Sort by severity
    sev_order = {AlertSeverity.CRITICAL: 0, AlertSeverity.HIGH: 1, AlertSeverity.MEDIUM: 2, AlertSeverity.LOW: 3, AlertSeverity.INFO: 4}
    alerts.sort(key=lambda a: sev_order.get(a.severity, 5))

    if args.json:
        data = [
            {
                "severity": a.severity.value,
                "direction": a.direction.value,
                "provider": a.provider.value,
                "model_id": a.model_id,
                "message": a.message,
                "detail": a.detail,
                "max_pct": round(a.max_pct, 1),
                "detected_at": a.detected_at.isoformat(),
            }
            for a in alerts
        ]
        print(json.dumps(data, indent=2))
        return

    try:
        from rich.console import Console

        console = Console()
        for a in alerts:
            icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵", "info": "ℹ️"}.get(a.severity.value, "•")
            console.print(f"{icon} [{a.severity.value.upper()}] {a.message}")
            console.print(f"   {a.detail}", style="dim")
    except ImportError:
        for a in alerts:
            print(f"[{a.severity.value.upper()}] {a.message}")
            print(f"  {a.detail}")


def cmd_trends(args: argparse.Namespace) -> None:
    """Show price trends for a model."""
    store = PriceStore(args.store)
    model = args.model or "gpt-4o"
    days = args.days or 30
    trend = compute_trends(store, model, days=days)
    store.close()

    if trend is None:
        print(f"No trend data for {model}. Run 'pricewatch scan --store <db>' multiple times first.", file=sys.stderr)
        return

    if args.json:
        data = {
            "provider": trend.provider.value,
            "model_id": trend.model_id,
            "direction": trend.direction,
            "total_pct": round(trend.total_pct, 2),
            "points": [
                {
                    "timestamp": p.timestamp.isoformat(),
                    "input": p.input_price,
                    "output": p.output_price,
                    "blended": p.blended,
                }
                for p in trend.points
            ],
        }
        print(json.dumps(data, indent=2))
        return

    arrow = {"decreasing": "📉", "increasing": "📈", "stable": "➡️"}.get(trend.direction, "•")
    print(f"{arrow} {trend.provider.value}/{trend.model_id}: {trend.direction} ({trend.total_pct:+.1f}% over {days}d)")
    for p in trend.points:
        print(f"  {p.timestamp.strftime('%Y-%m-%d')}  In=${p.input_price:.3f}  Out=${p.output_price:.3f}  Blended=${p.blended:.3f}")


def main() -> None:
    """Entry point for pricewatch CLI."""
    parser = argparse.ArgumentParser(
        prog="pricewatch",
        description="LLM Provider Price Intelligence Monitor",
    )
    parser.add_argument("--version", action="version", version=f"pricewatch {__version__}")
    sub = parser.add_subparsers(dest="command")

    # scan
    p_scan = sub.add_parser("scan", help="Scan all providers for current prices")
    p_scan.add_argument("--store", help="SQLite DB path to persist snapshot")
    p_scan.add_argument("--json", action="store_true", help="JSON output")

    # compare
    p_cmp = sub.add_parser("compare", help="Compare models across providers")
    p_cmp.add_argument("--tier", help="Filter by tier (flagship/mid/fast/reasoning/embedding)")
    p_cmp.add_argument("--models", help="Comma-separated model IDs to compare")
    p_cmp.add_argument("--sort", default="blended", help="Sort method: blended/input/output/context_efficiency")
    p_cmp.add_argument("--json", action="store_true", help="JSON output")

    # alerts
    p_alert = sub.add_parser("alerts", help="Show price change alerts")
    p_alert.add_argument("--store", required=True, help="SQLite DB path with stored snapshots")
    p_alert.add_argument("--since", help="Show alerts since (N d/m/y)")
    p_alert.add_argument("--json", action="store_true", help="JSON output")

    # trends
    p_trend = sub.add_parser("trends", help="Show price trends for a model")
    p_trend.add_argument("--model", help="Model ID to track")
    p_trend.add_argument("--days", type=int, default=30, help="Days to look back")
    p_trend.add_argument("--store", required=True, help="SQLite DB path")
    p_trend.add_argument("--json", action="store_true", help="JSON output")

    args = parser.parse_args()

    if args.command == "scan":
        cmd_scan(args)
    elif args.command == "compare":
        cmd_compare(args)
    elif args.command == "alerts":
        cmd_alerts(args)
    elif args.command == "trends":
        cmd_trends(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
