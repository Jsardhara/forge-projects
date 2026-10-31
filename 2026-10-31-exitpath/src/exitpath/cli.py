"""Command line: 0 clean / 1 findings / 2 unmeasurable. Read-only, never sends a key."""
import argparse
import json
import sys
from datetime import datetime, timezone

from .chains import CHAINS, collect_chains
from .fetcher import HttpFetcher
from .report import build_report, render_text
from .venues import VENUES, collect_venues


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _selected(all_items, wanted, key):
    if not wanted:
        return all_items
    keep = {w.strip().lower() for w in wanted.split(",") if w.strip()}
    return tuple(i for i in all_items if getattr(i, key).lower() in keep)


def build_parser():
    parser = argparse.ArgumentParser(
        prog="exitpath",
        description="Read-only exit readiness: can funds actually leave each venue and chain?",
    )
    parser.add_argument("--json", action="store_true", help="emit the machine-readable rollup")
    parser.add_argument("--quiet", action="store_true", help="print nothing; exit code only")
    parser.add_argument("--venues", default="", help="comma-separated venue slugs (default: all)")
    parser.add_argument("--chains", default="", help="comma-separated chain names (default: all)")
    parser.add_argument("--timeout", type=float, default=12.0, help="per-request timeout in seconds")
    parser.add_argument("--no-chains", action="store_true", help="skip the chain RPC layer")
    return parser


def main(argv=None, fetcher=None):
    args = build_parser().parse_args(argv)
    fetcher = fetcher or HttpFetcher(timeout=args.timeout)

    venues = collect_venues(fetcher, _selected(VENUES, args.venues, "slug"))
    chains = () if args.no_chains else collect_chains(
        fetcher.post_json, _selected(CHAINS, args.chains, "chain")
    )

    report = build_report(venues, chains, _now())
    if not args.quiet:
        if args.json:
            sys.stdout.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
        else:
            sys.stdout.write(render_text(report))
    return report["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
