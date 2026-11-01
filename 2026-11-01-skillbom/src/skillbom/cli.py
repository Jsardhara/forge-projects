"""Command line entry point. Exit codes are the contract: 0 clean, 1 finding, 2 unmeasurable."""

import argparse
import json
import os
import sys

from .ledger import diff_ledgers, ledger_from_json, ledger_to_json
from .models import Root
from .report import EXIT_UNMEASURABLE, exit_code, render_text
from .scan import default_roots, scan_roots

DESCRIPTION = (
    "Read-only capability ledger for the skills installed on this host. "
    "Never executes a skill script and never prints a credential value."
)


def build_parser():
    parser = argparse.ArgumentParser(prog="skillbom", description=DESCRIPTION)
    parser.add_argument(
        "--root",
        action="append",
        default=None,
        metavar="PATH",
        help="skill directory to audit (repeatable). Default: ~/.hermes/profiles/*/skills",
    )
    parser.add_argument(
        "--label",
        action="append",
        default=None,
        metavar="NAME",
        help="label for the matching --root (repeatable, same order)",
    )
    parser.add_argument(
        "--include-global",
        action="store_true",
        help="also audit ~/.hermes/skills (the shared store)",
    )
    parser.add_argument("--json", action="store_true", help="emit the ledger as JSON")
    parser.add_argument("--ledger-out", metavar="PATH", help="write the JSON ledger to PATH")
    parser.add_argument("--diff", metavar="PATH", help="diff against a previous ledger file")
    parser.add_argument("--top", type=int, default=10, help="skills in the authority shortlist (0 = off)")
    parser.add_argument("--quiet", action="store_true", help="no text report; exit code only")
    return parser


def resolve_roots(args):
    if not args.root:
        return default_roots(include_global=args.include_global)
    labels = args.label or []
    roots = []
    for index, path in enumerate(args.root):
        label = labels[index] if index < len(labels) else os.path.basename(os.path.abspath(path)) or path
        roots.append(Root(label=label, path=path, kind="profile"))
    if args.include_global:
        roots.extend(r for r in default_roots(include_global=True) if r.kind == "shared")
    return tuple(roots)


def _load_previous(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return ledger_from_json(json.load(fh))
    except OSError as exc:
        sys.stderr.write("skillbom: cannot read previous ledger %s: %s\n" % (path, exc.strerror or exc))
    except ValueError as exc:
        sys.stderr.write("skillbom: %s is not a skillbom ledger: %s\n" % (path, exc))
    return None


def _write_ledger(path, ledger):
    try:
        parent = os.path.dirname(os.path.abspath(path))
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(ledger_to_json(ledger), fh, indent=2, sort_keys=True)
            fh.write("\n")
    except OSError as exc:
        sys.stderr.write("skillbom: cannot write ledger %s: %s\n" % (path, exc.strerror or exc))
        return False
    return True


def main(argv=None):
    args = build_parser().parse_args(argv)
    roots = resolve_roots(args)
    if not roots:
        sys.stderr.write(
            "skillbom: no skill roots found (looked under ~/.hermes/profiles/*/skills); "
            "pass --root PATH\n"
        )
        return EXIT_UNMEASURABLE

    ledger = scan_roots(roots)

    drift = None
    if args.diff:
        previous = _load_previous(args.diff)
        if previous is None:
            return EXIT_UNMEASURABLE
        drift = diff_ledgers(previous, ledger)

    if args.ledger_out and not _write_ledger(args.ledger_out, ledger):
        return EXIT_UNMEASURABLE

    if args.json:
        json.dump(ledger_to_json(ledger), sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    elif not args.quiet:
        sys.stdout.write(render_text(ledger, drift=drift, top=args.top))

    return exit_code(ledger, drift)
