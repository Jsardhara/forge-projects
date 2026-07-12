"""darkwatch command-line interface.

Subcommands:
  scan FILE|URL   scan an HTML file (or '-' for stdin) and print a report.
                  Exit code 1 if band is NON_COMPLIANT (CI gate).
  checklist HTML  print per-regulation pass/fail checklist.
  report FILE     write markdown report to FILE (stdout if '-').
  rules           list the 8 registered detection rules.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .models import ComplianceBand
from .scanner import regulation_checklist, scan_html
from .reporter import to_json, to_markdown, to_text


def _read_html(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8")


def _url_for(path: str) -> str:
    return "stdin" if path == "-" else path


def cmd_scan(args: argparse.Namespace) -> int:
    html = _read_html(args.path)
    result = scan_html(html, _url_for(args.path))
    if args.format == "json":
        print(to_json(result))
    elif args.format == "text":
        print(to_text(result))
    else:
        print(to_markdown(result))
    return 1 if result.band == ComplianceBand.NON_COMPLIANT else 0


def cmd_checklist(args: argparse.Namespace) -> int:
    html = _read_html(args.path)
    checks = regulation_checklist(html, _url_for(args.path))
    worst = 0
    for c in checks:
        icon = {"pass": "[ok]", "warn": "[--]", "fail": "[XX]"}.get(c.status, "[??]")
        print(f"{icon} {c.regulation.value}  (findings={c.findings}, critical={c.critical})")
        if c.status == "fail":
            worst = 1
    return worst


def cmd_report(args: argparse.Namespace) -> int:
    html = _read_html(args.path)
    result = scan_html(html, _url_for(args.path))
    md = to_markdown(result)
    if args.out in (None, "-"):
        print(md)
    else:
        Path(args.out).write_text(md, encoding="utf-8")
        print(f"Report written to {args.out}")
    return 1 if result.band == ComplianceBand.NON_COMPLIANT else 0


def cmd_rules(args: argparse.Namespace) -> int:
    from .rules import ALL_RULES

    for r in ALL_RULES:
        print(f"{r.id:24s} [{r.severity.value:8s}] {r.regulation.value}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="darkwatch", description="Dark-pattern / consumer-protection compliance scanner."
    )
    sub = p.add_subparsers(dest="command", required=True)

    ps = sub.add_parser("scan", help="Scan an HTML file or stdin for dark patterns.")
    ps.add_argument("path", help="HTML file path, or '-' for stdin.")
    ps.add_argument("--format", choices=["text", "markdown", "json"], default="text")
    ps.set_defaults(func=cmd_scan)

    pc = sub.add_parser("checklist", help="Print per-regulation pass/fail checklist.")
    pc.add_argument("path", help="HTML file path, or '-' for stdin.")
    pc.set_defaults(func=cmd_checklist)

    pr = sub.add_parser("report", help="Write a markdown report to a file or stdout.")
    pr.add_argument("path", help="HTML file path, or '-' for stdin.")
    pr.add_argument("--out", help="Output markdown file (default: stdout).")
    pr.set_defaults(func=cmd_report)

    prl = sub.add_parser("rules", help="List the registered detection rules.")
    prl.set_defaults(func=cmd_rules)
    return p


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
