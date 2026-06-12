"""CLI for AgentWatch."""

from __future__ import annotations

import argparse
import json
import sys
import time

from agentwatch.db import (
    get_db,
    register_agent,
    list_agents,
    set_budget,
    create_guardrail_probe,
    list_guardrail_probes,
    list_alerts,
)
from agentwatch.cost import check_budget, estimate_cost
from agentwatch.guardrail import run_probe, get_drift_trend


def cmd_init(args):
    """Initialize AgentWatch — creates default agents and probes."""
    conn = get_db()

    # Register a default agent
    register_agent(conn, "default", "Default Agent", "openai")
    set_budget(conn, "default", daily_limit_usd=5.0, monthly_limit_usd=100.0)

    # Create a default guardrail probe
    create_guardrail_probe(
        conn,
        "default-openai",
        "OpenAI Baseline Check",
        "openai",
        "gpt-4o",
        "Explain what Python is and why it is used in machine learning.",
        json.dumps(["python", "programming", "machine learning", "language"]),
    )

    print("AgentWatch initialized.")
    print("  Agent: default (openai) — daily $5, monthly $100")
    print("  Probe: default-openai — checks OpenAI baseline")


def cmd_check(args):
    """Run cost and guardrail checks."""
    conn = get_db()

    agents = list_agents(conn)
    if not agents:
        print("No agents registered. Run 'agentwatch init' first.")
        return

    for agent in agents:
        agent_id = agent["agent_id"]
        print(f"\n── Agent: {agent['name']} ({agent_id}) ──")

        # Budget check
        report = check_budget(conn, agent_id)
        print(f"  Daily:   ${report.daily_spend:.4f} / ${report.daily_limit:.2f} ({report.daily_pct}%)")
        print(f"  Monthly: ${report.monthly_spend:.4f} / ${report.monthly_limit:.2f} ({report.monthly_pct}%)")
        if report.budget_exceeded:
            print("  STATUS: ⚠ BUDGET EXCEEDED")
        elif report.alert_triggered:
            print("  STATUS: ⚡ Alert threshold reached")
        else:
            print("  STATUS: ✓ OK")

    # Guardrail checks
    probes = list_guardrail_probes(conn)
    for probe in probes:
        print(f"\n── Guardrail: {probe['name']} ({probe['probe_id']}) ──")
        result = run_probe(conn, probe["probe_id"])
        print(f"  Passed:     {'✓' if result.passed else '✗ FAILED'}")
        print(f"  Drift:      {result.drift_score:.2f}")
        print(f"  Found:      {', '.join(result.keywords_found) or '(none)'}")
        print(f"  Missing:    {', '.join(result.keywords_missing) or '(none)'}")

    # Show alerts
    alerts = list_alerts(conn, unread_only=True, limit=10)
    if alerts:
        print(f"\n── {len(alerts)} Unread Alert(s) ──")
        for a in alerts:
            print(f"  [{a['severity'].upper()}] {a['message']}")


def cmd_serve(args):
    """Start the API server."""
    import uvicorn
    from agentwatch.api import app

    port = getattr(args, "port", 8080)
    print(f"Starting AgentWatch API on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)


def cmd_estimate(args):
    """Estimate cost for token usage."""
    cost = estimate_cost(args.tokens_in, args.tokens_out, args.model)
    print(f"Model: {args.model}")
    print(f"Tokens: {args.tokens_in} in, {args.tokens_out} out")
    print(f"Estimated cost: ${cost:.6f}")


def main():
    parser = argparse.ArgumentParser(prog="agentwatch", description="AI Agent Cost & Guardrail Monitoring")
    sub = parser.add_subparsers(dest="command")

    # init
    sub.add_parser("init", help="Initialize AgentWatch")

    # check
    sub.add_parser("check", help="Run cost + guardrail checks")

    # serve
    serve_p = sub.add_parser("serve", help="Start API server")
    serve_p.add_argument("--port", type=int, default=8080)

    # estimate
    est_p = sub.add_parser("estimate", help="Estimate API cost")
    est_p.add_argument("--tokens-in", type=int, required=True)
    est_p.add_argument("--tokens-out", type=int, required=True)
    est_p.add_argument("--model", default="gpt-4o")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "init": cmd_init,
        "check": cmd_check,
        "serve": cmd_serve,
        "estimate": cmd_estimate,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
