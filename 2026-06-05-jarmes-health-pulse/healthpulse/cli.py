"""CLI entry point for Jarmes Health Pulse."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        prog="healthpulse",
        description="Jarmes Health Pulse — log-based system health dashboard",
    )
    sub = parser.add_subparsers(dest="command")

    # serve
    serve_parser = sub.add_parser("serve", help="Start the health dashboard server")
    serve_parser.add_argument("--host", default="0.0.0.0")
    serve_parser.add_argument("--port", type=int, default=8742)
    serve_parser.add_argument("--log-path", action="append", dest="log_paths", default=[])
    serve_parser.add_argument("--max-lines", type=int, default=5000)

    # summary
    summary_parser = sub.add_parser("summary", help="Print a text summary of system health")
    summary_parser.add_argument("--log-path", action="append", dest="log_paths", default=[])
    summary_parser.add_argument("--max-lines", type=int, default=5000)

    args = parser.parse_args()

    if args.command == "serve":
        import uvicorn
        from healthpulse.server import app
        print(f"⚡ Jarmes Health Pulse starting at http://{args.host}:{args.port}")
        uvicorn.run(app, host=args.host, port=args.port)

    elif args.command == "summary":
        from healthpulse.aggregator import build_system_health
        from healthpulse.models import HealthStatus

        paths = args.log_paths if args.log_paths else None
        health = build_system_health(log_paths=paths, max_lines=args.max_lines)

        status_icons = {
            HealthStatus.HEALTHY: "✅",
            HealthStatus.DEGRADED: "⚠️",
            HealthStatus.FAILING: "🔴",
            HealthStatus.UNKNOWN: "❓",
        }
        icon = status_icons.get(health.overall_status, "❓")
        print(f"\n{icon} System Health: {health.overall_status.value.upper()}")
        print(f"   Lines parsed: {health.total_lines_parsed:,}")
        print(f"   Errors: {health.total_errors:,}  Warnings: {health.total_warnings:,}")
        print(f"   Log sources: {len(health.log_sources)}")
        print(f"   Jobs tracked: {len(health.jobs)}")

        if health.jobs:
            print(f"\n{'Job':<40} {'Status':<12} {'Errors':>7} {'Success':>7} {'Rate':>7}")
            print("─" * 76)
            for j in health.jobs:
                jicon = {
                    HealthStatus.HEALTHY: "✅",
                    HealthStatus.DEGRADED: "⚠️",
                    HealthStatus.FAILING: "🔴",
                    HealthStatus.UNKNOWN: "❓",
                }.get(j.status, "❓")
                rate = f"{j.error_rate * 100:.1f}%"
                print(f"{jicon} {j.name:<38} {j.status.value:<12} {j.total_errors:>7} {j.total_successes:>7} {rate:>7}")

        if health.top_error_patterns:
            print(f"\nTop Error Patterns:")
            for i, p in enumerate(health.top_error_patterns[:5], 1):
                print(f"  {i}. ×{p.count}  {p.pattern[:80]}")
                if p.suggestion:
                    print(f"     💡 {p.suggestion[:120]}")

        print()

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
