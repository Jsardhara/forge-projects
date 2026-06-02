"""CLI for AI Cost Guard."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone

from aicostguard.pricing import ALL_PRICES, estimate_cost, get_price
from aicostguard.tracker import Budget, UsageRecord, UsageTracker


def cmd_estimate(args):
    """Estimate cost for a given usage."""
    cost = estimate_cost(args.provider, args.model, args.input_tokens, args.output_tokens)
    if cost == 0:
        print(f"Warning: No pricing found for {args.provider}/{args.model}")
        print("Available models:")
        for prov, models in ALL_PRICES.items():
            for m in models:
                print(f"  {prov}/{m}")
    print(f"Estimated cost: ${cost:.6f}")
    print(f"  Provider: {args.provider}")
    print(f"  Model: {args.model}")
    print(f"  Input tokens: {args.input_tokens:,}")
    print(f"  Output tokens: {args.output_tokens:,}")


def cmd_track(args):
    """Record a usage event."""
    tracker = UsageTracker(args.db)
    record = UsageRecord(
        provider=args.provider,
        model=args.model,
        input_tokens=args.input_tokens,
        output_tokens=args.output_tokens,
        team_id=args.team,
        tags=args.tags,
    )
    row_id = tracker.record_usage(record)
    print(f"Recorded usage #{row_id}: ${record.estimated_cost:.6f}")


def cmd_spend(args):
    """Show current spend."""
    tracker = UsageTracker(args.db)
    total = tracker.get_total_spend(team_id=args.team, provider=args.provider, period=args.period)
    print(f"Total spend ({args.period}, team={args.team}, provider={args.provider}): ${total:.4f}")

    by_model = tracker.get_spend_by_model(team_id=args.team, period=args.period)
    if by_model:
        print(f"\n{'Provider':<12} {'Model':<35} {'Cost':>10} {'Input':>10} {'Output':>10} {'Calls':>6}")
        print("-" * 85)
        for r in by_model:
            print(f"{r['provider']:<12} {r['model']:<35} ${r['total_cost']:>8.4f} {r['total_input']:>10,} {r['total_output']:>10,} {r['call_count']:>6}")


def cmd_budget(args):
    """Manage budgets."""
    tracker = UsageTracker(args.db)

    if args.budget_action == "set":
        budget = Budget(
            team_id=args.team,
            provider=args.provider,
            model=args.model,
            period=args.period,
            limit_usd=args.limit,
            alert_at_pct=args.alert_pct,
        )
        row_id = tracker.set_budget(budget)
        print(f"Budget #{row_id} set: ${args.limit:.2f} ({args.period}) for {args.provider}/{model} (team={args.team})")

    elif args.budget_action == "list":
        budgets = tracker.get_budgets(team_id=args.team)
        if not budgets:
            print("No budgets set.")
        else:
            print(f"{'ID':>4} {'Provider':<12} {'Model':<30} {'Period':<8} {'Limit':>10} {'Alert%':>7}")
            print("-" * 75)
            for b in budgets:
                print(f"{b['id']:>4} {b['provider']:<12} {b['model']:<30} {b['period']:<8} ${b['limit_usd']:>8.2f} {b['alert_at_pct']:>6.0f}%")

    elif args.budget_action == "check":
        alerts = tracker.check_budgets(team_id=args.team)
        if not alerts:
            print("All budgets OK.")
        else:
            for a in alerts:
                icon = "🔴" if a.severity == "alert" else "🟡"
                print(f"{icon} [{a.severity.upper()}] {a.message}")


def cmd_alerts(args):
    """Show alerts."""
    tracker = UsageTracker(args.db)
    alerts = tracker.get_alerts(team_id=args.team, unacknowledged_only=not args.all)
    if not alerts:
        print("No alerts.")
    else:
        for a in alerts:
            ack = "✓" if a["acknowledged"] else "○"
            print(f"[{ack}] {a['created_at']} [{a['severity']}] {a['message']}")


def cmd_waste(args):
    """Show waste report."""
    tracker = UsageTracker(args.db)
    waste = tracker.get_waste_report(team_id=args.team, period=args.period)
    if not waste:
        print("No waste detected. Good job!")
    else:
        total_savings = sum(w["estimated_savings"] for w in waste)
        print(f"Potential savings: ${total_savings:.4f} ({args.period})\n")
        for w in waste:
            print(f"  {w['current_provider']}/{w['current_model']}")
            print(f"    Current cost: ${w['current_cost']:.4f} ({w['call_count']} calls)")
            print(f"    Suggest: {w['suggested_provider']}/{w['suggested_model']}")
            print(f"    Est. savings: ${w['estimated_savings']:.4f} ({w['savings_pct']}%)\n")


def cmd_prices(args):
    """List all known prices."""
    for provider, models in ALL_PRICES.items():
        print(f"\n{provider.upper()}")
        print(f"  {'Model':<40} {'Input/1K':>10} {'Output/1K':>10}")
        print(f"  {'-'*60}")
        for model, prices in models.items():
            inp = prices.get("input", 0)
            out = prices.get("output", 0)
            print(f"  {model:<40} ${inp:>9.6f} ${out:>9.6f}")


def main():
    parser = argparse.ArgumentParser(
        prog="ai-cost-guard",
        description="AI Cost Guard — Track and optimize team AI API spending",
    )
    parser.add_argument("--db", default="aicostguard.db", help="Database path")
    parser.add_argument("--team", default="default", help="Team ID")

    sub = parser.add_subparsers(dest="command")

    # estimate
    p_est = sub.add_parser("estimate", help="Estimate cost for token usage")
    p_est.add_argument("provider", help="Provider (openai, anthropic, google)")
    p_est.add_argument("model", help="Model name")
    p_est.add_argument("input_tokens", type=int, help="Input tokens")
    p_est.add_argument("output_tokens", type=int, help="Output tokens")
    p_est.set_defaults(func=cmd_estimate)

    # track
    p_track = sub.add_parser("track", help="Record a usage event")
    p_track.add_argument("provider", help="Provider")
    p_track.add_argument("model", help="Model name")
    p_track.add_argument("input_tokens", type=int, help="Input tokens")
    p_track.add_argument("output_tokens", type=int, help="Output tokens")
    p_track.add_argument("--tags", default="", help="Tags")
    p_track.set_defaults(func=cmd_track)

    # spend
    p_spend = sub.add_parser("spend", help="Show current spend")
    p_spend.add_argument("--provider", default="all", help="Filter by provider")
    p_spend.add_argument("--period", default="daily", choices=["daily", "weekly", "monthly"], help="Period")
    p_spend.set_defaults(func=cmd_spend)

    # budget
    p_budget = sub.add_parser("budget", help="Manage budgets")
    p_budget.add_argument("budget_action", choices=["set", "list", "check"], help="Action")
    p_budget.add_argument("--provider", default="all", help="Provider filter")
    p_budget.add_argument("--model", default="all", help="Model filter")
    p_budget.add_argument("--period", default="daily", choices=["daily", "weekly", "monthly"])
    p_budget.add_argument("--limit", type=float, default=0, help="Budget limit in USD")
    p_budget.add_argument("--alert-pct", type=float, default=80, help="Alert at % of budget")
    p_budget.set_defaults(func=cmd_budget)

    # alerts
    p_alerts = sub.add_parser("alerts", help="Show alerts")
    p_alerts.add_argument("--all", action="store_true", help="Show all alerts including acknowledged")
    p_alerts.set_defaults(func=cmd_alerts)

    # waste
    p_waste = sub.add_parser("waste", help="Show waste report")
    p_waste.add_argument("--period", default="daily", choices=["daily", "weekly", "monthly"])
    p_waste.set_defaults(func=cmd_waste)

    # prices
    p_prices = sub.add_parser("prices", help="List all known prices")
    p_prices.set_defaults(func=cmd_prices)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
