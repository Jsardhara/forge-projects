"""CLI for ModelRouter."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone


def cmd_demo(args: argparse.Namespace) -> None:
    """Run a demo showing router capabilities."""
    from model_router import Provider, Router, CircuitBreaker

    glm = Provider(
        name="glm-5.2",
        base_url="https://api.z.ai/v1",
        api_key="demo-key",
        model_map={"gpt-4o": "z-ai/glm-5.2", "gpt-4o-mini": "z-ai/glm-5.2"},
        input_cost_per_mtok=1.40,
        output_cost_per_mtok=4.40,
    )
    openai = Provider(
        name="openai",
        base_url="https://api.openai.com/v1",
        api_key="demo-key",
        model_map={},
        input_cost_per_mtok=5.0,
        output_cost_per_mtok=15.0,
    )
    router = Router(primary=glm, fallback=openai)

    # Simulate requests
    for i in range(3):
        result = router.route(
            model="gpt-4o",
            messages=[{"role": "user", "content": f"Hello {i}"}],
            input_tokens=100,
            output_tokens=50,
        )
        print(f"  Request {i+1}: provider={result.provider}, model={result.model}, "
              f"cost=${result.cost_usd:.6f}, fallback={result.fallback_used}")

    # Mark primary unhealthy, show fallback
    print("\n  Simulating primary failure...")
    for _ in range(3):
        router.mark_unhealthy("glm-5.2")

    result = router.route(
        model="gpt-4o",
        messages=[{"role": "user", "content": "Hello after failure"}],
        input_tokens=100,
        output_tokens=50,
    )
    print(f"  After failure: provider={result.provider}, fallback={result.fallback_used}")

    print(f"\n  Total cost: ${router.total_cost():.6f}")
    print(f"  Total requests: {router.total_requests()}")
    print(f"  Fallback count: {router.fallback_count()}")


def cmd_health(args: argparse.Namespace) -> None:
    """Check provider health."""
    from model_router import Provider, Router

    provider = Provider(
        name="custom",
        base_url=args.base_url,
        api_key=getattr(args, "api_key", "") or "",
    )
    router = Router(primary=provider)
    status = router.health_check()
    print(json.dumps({
        "provider": status.provider,
        "healthy": status.healthy,
        "latency_ms": round(status.latency_ms, 2),
        "checked_at": status.checked_at,
        "error": status.error,
    }, indent=2))


def cmd_cost(args: argparse.Namespace) -> None:
    """Calculate cost for given token counts."""
    from model_router import Provider

    provider = Provider(
        name=args.provider or "glm-5.2",
        base_url="",
        input_cost_per_mtok=args.input_cost,
        output_cost_per_mtok=args.output_cost,
    )
    cost = provider.calculate_cost(args.input_tokens, args.output_tokens)
    print(json.dumps({
        "provider": provider.name,
        "input_tokens": args.input_tokens,
        "output_tokens": args.output_tokens,
        "cost_usd": round(cost, 6),
        "cost_per_mtok_input": args.input_cost,
        "cost_per_mtok_output": args.output_cost,
    }, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(prog="model-router", description="GLM-5.2 OpenAI-compatible gateway")
    sub = parser.add_subparsers(dest="command")

    # demo
    demo_p = sub.add_parser("demo", help="Run a demo")

    # health
    health_p = sub.add_parser("health", help="Check provider health")
    health_p.add_argument("--base-url", required=True, help="Provider base URL")
    health_p.add_argument("--api-key", default="", help="API key")

    # cost
    cost_p = sub.add_parser("cost", help="Calculate request cost")
    cost_p.add_argument("--provider", default="glm-5.2", help="Provider name")
    cost_p.add_argument("--input-tokens", type=int, required=True)
    cost_p.add_argument("--output-tokens", type=int, required=True)
    cost_p.add_argument("--input-cost", type=float, default=1.40, help="Cost per M input tokens")
    cost_p.add_argument("--output-cost", type=float, default=4.40, help="Cost per M output tokens")

    args = parser.parse_args()
    if args.command == "demo":
        cmd_demo(args)
    elif args.command == "health":
        cmd_health(args)
    elif args.command == "cost":
        cmd_cost(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
