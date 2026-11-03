"""posture CLI — one exit code for five verifiers, one transition list per morning."""

import argparse
import os
import sys
import time
from typing import List, Optional

from .discover import discover, missing
from .models import ERROR, FINDINGS, UNMEASURABLE, VerifierResult
from .report import render_json, render_text
from .runner import run_verifier
from .state import diff_results, load_state, save_state, _utc_now

PROJECT_DIR = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
DEFAULT_REPO_ROOT = os.path.dirname(PROJECT_DIR)
DEFAULT_STATE = os.path.expanduser("~/.local/state/posture/state.json")
#: posture must never discover and run itself — that is a timeout, not a posture.
SELF_NAME = "posture"



def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="posture",
        description=(
            "Run every read-only verifier in this repo, report only what changed, "
            "and exit 0 (clear) / 1 (needs a human) / 2 (partial or unmeasured)."
        ),
    )
    p.add_argument("--repo-root", default=DEFAULT_REPO_ROOT,
                   help="directory containing the dated verifier projects")
    p.add_argument("--only", default="",
                   help="comma-separated verifier names to run")
    p.add_argument("--all", action="store_true",
                   help="also run dated projects that are not registered verifiers")

    p.add_argument("--state", default=os.environ.get("POSTURE_STATE", DEFAULT_STATE),
                   help="baseline state file")
    p.add_argument("--no-save", action="store_true",
                   help="run and report without writing the baseline")
    p.add_argument("--diff", action="store_true",
                   help="report transitions against the saved baseline")
    p.add_argument("--json", action="store_true", help="machine-readable rollup")
    p.add_argument("--quiet", action="store_true",
                   help="no output when the run is clean")
    p.add_argument("--timeout", type=float, default=120.0,
                   help="per-verifier timeout in seconds (default 120)")
    return p


def _exit_code(results) -> int:
    if any(r.status in (UNMEASURABLE, ERROR) for r in results):
        return 2
    if any(r.status == FINDINGS for r in results):
        return 1
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    args = _parser().parse_args(argv)
    only = [n.strip() for n in args.only.split(",") if n.strip()] or None

    try:
        verifiers = discover(
            args.repo_root,
            only=only,
            include_unknown=args.all,
            exclude=[SELF_NAME],
        )
    except OSError as exc:
        print(
            f"posture: cannot read --repo-root {args.repo_root!r}: {exc}",
            file=sys.stderr,
        )
        return 2

    for name in missing(only, verifiers):
        print(f"posture: no verifier named {name!r} under {args.repo_root}", file=sys.stderr)
        return 2

    if not verifiers:
        print(
            f"posture: no verifiers found under {args.repo_root} "
            "(expected YYYY-MM-DD-<name>/src/<module>/cli.py)",
            file=sys.stderr,
        )
        return 2

    verifier_state_dir = os.path.join(
        os.path.dirname(os.path.abspath(args.state)), "verifiers"
    )
    cve = os.environ.get("POSTURE_CVE", "CVE-2026-98432")

    started = time.monotonic()
    results: List[VerifierResult] = []
    for verifier in verifiers:
        argv_for_child = verifier.spec.expanded_args(verifier_state_dir, cve)
        results.append(
            run_verifier(
                verifier,
                timeout=args.timeout,
                args=argv_for_child,
            )
        )
    elapsed = time.monotonic() - started

    generated_at = _utc_now()
    exit_code = _exit_code(results)
    previous = load_state(args.state) if args.diff else None
    transitions = diff_results(previous, {r.name: r for r in results}) if args.diff else []
    baseline = args.diff and previous is None

    if not args.no_save:
        try:
            save_state(args.state, {r.name: r for r in results}, now=generated_at)
        except OSError as exc:
            print(f"posture: could not write state {args.state!r}: {exc}", file=sys.stderr)

    if args.json:
        print(
            render_json(
                results, transitions, baseline, generated_at, args.repo_root, exit_code
            )
        )
        if exit_code != 0:
            print(
                f"posture: {_headline(results)} ({elapsed:.1f}s)",
                file=sys.stderr,
            )
        return exit_code

    if args.quiet and exit_code == 0:
        return 0

    print(
        render_text(
            results,
            transitions,
            baseline,
            generated_at,
            args.state if not args.no_save else None,
        )
    )
    print(f"({elapsed:.1f}s)", file=sys.stderr)
    return exit_code


def _headline(results) -> str:
    broken = sorted(r.name for r in results if r.status in (UNMEASURABLE, ERROR))
    if broken:
        return f"partial: {', '.join(broken)} could not be measured"
    findings = sorted(r.name for r in results if r.status == FINDINGS)
    if findings:
        return f"needs a human: {', '.join(findings)}"
    return "all clear"


if __name__ == "__main__":
    sys.exit(main())
