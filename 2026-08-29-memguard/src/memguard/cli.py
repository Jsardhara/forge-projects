"""memguard.cli -- command-line interface."""
from __future__ import annotations

import argparse
import json
import sys
from typing import List

from . import __version__
from .models import Verdict
from .scanner import aggregate_score, aggregate_verdict, scan_paths


def _print_plain(results) -> None:
    if not results:
        print("No context files found to scan.")
        return
    for r in results:
        if r.error:
            print(f"[ERROR] {r.path}: {r.error}")
            continue
        print(f"{r.verdict().value:9s} {r.score():5.1f}/100  {r.path}  ({len(r.findings)} finding(s))")
        for f in sorted(r.findings, key=lambda x: (-x.severity.weight, x.line)):
            print(f"    - [{f.severity.value:8s}] {f.rule_id} {f.category} "
                  f"line {f.line}: {f.message}")
            print(f"        matched: {f.matched_text[:120]!r}")
    agg = aggregate_score(results)
    verdict = aggregate_verdict(results)
    print(f"\nOverall: {verdict.value}  ({agg:.1f}/100)  across {len(results)} file(s)")


def run_scan(args) -> int:
    results = scan_paths(args.path, recursive=not args.no_recursive)
    if args.json:
        payload = {
            "version": __version__,
            "overall_verdict": aggregate_verdict(results).value,
            "overall_score": aggregate_score(results),
            "files": [r.to_dict() for r in results],
        }
        json.dump(payload, sys.stdout, indent=2)
    else:
        _print_plain(results)
    return 0


def run_check(args) -> int:
    """CI gate: exit 0 if risk below threshold, 1 if a HIGH/CRITICAL is present or
    overall score exceeds the threshold, 2 on any read error."""
    results = scan_paths(args.path, recursive=not args.no_recursive)
    for r in results:
        if r.error:
            if args.json:
                json.dump({"error": r.to_dict()}, sys.stdout)
            else:
                print(f"[ERROR] {r.path}: {r.error}")
            return 2
    score = aggregate_score(results)
    verdict = aggregate_verdict(results)
    has_high = any(
        f.severity.value in ("HIGH", "CRITICAL") for r in results for f in r.findings
    )
    fail = has_high or score >= args.score_threshold

    if args.json:
        json.dump({
            "gate": "PASS" if not fail else "FAIL",
            "overall_verdict": verdict.value,
            "overall_score": score,
            "threshold": args.score_threshold,
            "files": [r.to_dict() for r in results],
        }, sys.stdout, indent=2)
    else:
        print(f"gate: {'PASS' if not fail else 'FAIL'}  "
              f"overall {verdict.value} ({score:.1f}/100)  threshold {args.score_threshold}  "
              f"files={len(results)}")
        for r in results:
            for f in r.findings:
                print(f"    - [{f.severity.value:8s}] {r.path}:{f.line} {f.rule_id} {f.message}")
    return 1 if fail else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="memguard",
        description="Static scanner for AI-agent memory poisoning & prompt-injection "
                    "in memory/prompt/context files. Zero deps, no LLM.",
    )
    parser.add_argument("--version", action="version", version=f"memguard {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    scan = sub.add_parser("scan", help="Scan files/dirs and report findings.")
    scan.add_argument("path", nargs="+", help="File or directory to scan.")
    scan.add_argument("--no-recursive", action="store_true", help="Do not recurse into dirs.")
    scan.add_argument("--json", action="store_true", help="Emit JSON.")
    scan.set_defaults(func=run_scan)

    check = sub.add_parser("check", help="CI gate: exit non-zero on high risk.")
    check.add_argument("path", nargs="+", help="File or directory to scan.")
    check.add_argument("--no-recursive", action="store_true")
    check.add_argument("--json", action="store_true")
    check.add_argument("--score-threshold", type=float, default=40.0,
                       help="Fail when overall score >= this (default 40).")
    check.set_defaults(func=run_check)

    return parser


def main(argv: List[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())