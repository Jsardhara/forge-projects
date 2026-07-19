"""mcpshield command-line interface.

Usage:
    mcpshield check <spec.json> [--json]
    mcpshield check --dir <dir> [--json]
    mcpshield version

Exit code is 1 when any analyzed server FAILs (CI gate), 0 otherwise.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from mcpshield import analyze, spec_from_dict
from mcpshield.models import Report


def _load_specs(paths) -> list:
    specs = []
    for p in paths:
        data = json.loads(Path(p).read_text(encoding="utf-8"))
        # A spec file may be a single spec or {"servers": [..]}
        if isinstance(data, list):
            specs.extend(spec_from_dict(d) for d in data)
        elif isinstance(data, dict) and "servers" in data:
            specs.extend(spec_from_dict(d) for d in data["servers"])
        else:
            specs.append(spec_from_dict(data))
    return specs


def _load_dir(d: str) -> list:
    specs = []
    for f in sorted(Path(d).glob("*.json")):
        try:
            specs.extend(_load_specs([f]))
        except Exception as e:  # noqa: BLE001
            print(f"  ! skip {f.name}: {e}", file=sys.stderr)
    return specs


def _print_report(report: Report) -> None:
    bar = {"PASS": "PASS", "WARN": "WARN", "FAIL": "FAIL"}[report.band]
    print(f"=== mcpshield: {report.server} ===")
    print(f"  verdict : {bar}   risk_score={report.risk_score}/100")
    print(f"  findings: {len(report.findings)}")
    if not report.findings:
        print("  (no issues detected)")
        return
    order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
    for f in sorted(report.findings, key=lambda x: order.get(x.severity, 9)):
        print(f"  [{f.severity:8}] {f.title}")
        print(f"             {f.detail}")
        if f.recommendation:
            print(f"             fix: {f.recommendation}")


def cmd_check(args: argparse.Namespace) -> int:
    specs = []
    if args.dir:
        specs = _load_dir(args.dir)
    if args.paths:
        specs.extend(_load_specs(args.paths))
    if not specs:
        print("error: no spec files provided", file=sys.stderr)
        return 2

    reports = [analyze(s) for s in specs]
    if args.json:
        out = [r.to_dict() for r in reports]
        print(json.dumps(out if len(out) > 1 else out[0], indent=2))
    else:
        for r in reports:
            _print_report(r)
            print()

    worst_fail = any(r.failed for r in reports)
    return 1 if worst_fail else 0


def build_parser() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="mcpshield",
        description="Secure MCP server health-check & sandbox policy engine.",
    )
    sub = parser.add_subparsers(dest="command")

    p_check = sub.add_parser("check", help="analyze one or more MCP server specs")
    p_check.add_argument("paths", nargs="*", help="path(s) to spec JSON file(s)")
    p_check.add_argument("--dir", help="directory of *.json spec files to batch")
    p_check.add_argument("--json", action="store_true", help="emit JSON report")
    p_check.set_defaults(func=cmd_check)

    sub.add_parser("version", help="print version").set_defaults(
        func=lambda a: print(__import__("mcpshield").__version__)
    )
    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        return 0
    if not hasattr(args, "func"):
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
