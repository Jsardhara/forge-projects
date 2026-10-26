"""Command line surface.

Exit codes are the contract:

  0  nothing found, or nothing at or above the --fail-on threshold
  1  at or above the --fail-on threshold (default: an affected target)
  2  the run could not answer the question (bad rules, unreadable vendor path)

2 matters as much as 1: a CI gate that returns 0 because it could not read its own
rule file is the silent-death failure mode this tool is supposed to prevent.
"""

from __future__ import annotations

import argparse
import sys
from typing import Optional, Sequence

from .attest import attest
from .inventory import (
    SubprocessRunner,
    discover_python_paths,
    find_node,
    find_pythons,
    find_system_packages,
)
from .report import render_json, render_text
from .rules import RuleError, RuleSet, default_rules_path
from .vendored import scan_tree

__all__ = ["main", "build_parser"]

FAIL_ON_CHOICES = ("never", "exposed", "unknown")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="decoderattest",
        description="Attest which Brotli decoder is actually loaded on this host.",
    )
    parser.add_argument("--rules", default=None, help="rule file (default: bundled advisory rules)")
    parser.add_argument("--python", action="append", default=[], metavar="PATH",
                        help="extra Python interpreter to probe (repeatable)")
    parser.add_argument("--scan-vendor", action="append", default=[], metavar="DIR",
                        help="directory to scan for vendored brotli/ copies (repeatable)")
    parser.add_argument("--no-node", action="store_true", help="skip Node.js discovery")
    parser.add_argument("--no-python", action="store_true", help="skip Python interpreters")
    parser.add_argument("--no-system", action="store_true", help="skip distribution packages")
    parser.add_argument("--json", action="store_true", help="emit JSON instead of text")
    parser.add_argument("--fail-on", choices=FAIL_ON_CHOICES, default="exposed",
                        help="lowest verdict that exits 1 (default: exposed)")
    return parser


def main(argv: Optional[Sequence[str]] = None, runner=None, out=None) -> int:
    args = build_parser().parse_args(argv)
    stream = out if out is not None else sys.stdout
    runner = runner or SubprocessRunner()

    try:
        rules = RuleSet.load(args.rules or default_rules_path())
    except RuleError as exc:
        print("rules error: %s" % exc, file=stream)
        return 2

    vendors = []
    for root in args.scan_vendor:
        try:
            vendors.extend(scan_tree(root))
        except OSError as exc:
            print("vendor scan error: %s" % exc, file=stream)
            return 2

    try:
        nodes = [] if args.no_node else find_node(runner)
        pythons = [] if args.no_python else find_pythons(
            runner, discover_python_paths(runner, args.python)
        )
        packages = [] if args.no_system else find_system_packages(
            runner, _system_package_names(rules)
        )
    except OSError as exc:
        print("probe error: %s" % exc, file=stream)
        return 2

    result = attest(rules, nodes=nodes, pythons=pythons, packages=packages, vendored=vendors)
    print(render_json(result) if args.json else render_text(result), file=stream)
    return _exit_code(result.verdict, args.fail_on)


def _system_package_names(rules: RuleSet):
    names = []
    for product in rules.products:
        if product.ecosystem != "system":
            continue
        for name in product.packages:
            if name not in names:
                names.append(name)
    return names


def _exit_code(verdict: str, fail_on: str) -> int:
    if fail_on == "never":
        return 0
    if verdict == "EXPOSED":
        return 1
    if fail_on == "unknown" and verdict == "UNKNOWN":
        return 1
    return 0
