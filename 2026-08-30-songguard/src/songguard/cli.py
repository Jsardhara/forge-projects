"""CLI for songguard: screen (human/JSON) and check (CI gate)."""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import List

from .models import Severity, Verdict
from .scanner import SongguardError, screen_file, screen_text, load_catalog

EXIT_OK = 0
EXIT_FAIL = 1
EXIT_ERROR = 2

_THRESHOLD_DEFAULT = 60


def _match_to_dict(m):
    return {
        "reference": m.ref_name,
        "containment": m.containment,
        "jaccard": m.jaccard,
        "longest_common_phrase_tokens": m.longest_run,
        "sampled_phrase": m.sampled_phrase,
        "severity": m.severity.value,
    }


def _report_to_dict(r):
    return {
        "input": r.input_path,
        "score": r.score,
        "verdict": r.verdict.value,
        "flagged_references": r.flag_count(),
        "review_references": r.review_count(),
        "matches": [_match_to_dict(m) for m in r.matches],
    }


def _format_human(r) -> str:
    lines: List[str] = []
    lines.append(f"input  : {r.input_path}")
    lines.append(f"score  : {r.score}/100")
    lines.append(f"verdict: {r.verdict.value}")
    for m in r.matches:
        tag = m.severity.value
        run = f"run={m.longest_run}" if m.longest_run else "run=0"
        phrase = f"  sampled: \"{m.sampled_phrase}\"" if m.sampled_phrase else ""
        lines.append(f"  [{tag}] {m.ref_name}  containment={m.containment:.2f} "
                     f"jaccard={m.jaccard:.2f} {run}{phrase}")
    return "\n".join(lines)


def cmd_screen(args) -> int:
    refs = load_catalog(args.reference)
    if args.input == "-":
        report = screen_text(sys.stdin.read(), refs)
        report.input_path = "<stdin>"
    else:
        report = screen_file(args.input, args.reference)
    if args.json:
        print(json.dumps(_report_to_dict(report), indent=2))
    else:
        print(_format_human(report))
    return EXIT_OK


def cmd_check(args) -> int:
    try:
        if args.input == "-":
            refs = load_catalog(args.reference)
            report = screen_text(sys.stdin.read(), refs)
            report.input_path = "<stdin>"
        else:
            report = screen_file(args.input, args.reference)
    except SongguardError:
        print(f"songguard: error reading input or reference", file=sys.stderr)
        return EXIT_ERROR
    ok = report.verdict == Verdict.CLEAR and report.score < args.threshold
    if args.json:
        d = _report_to_dict(report)
        d["gate"] = "PASS" if ok else "FAIL"
        print(json.dumps(d, indent=2))
    else:
        print(f"songguard: {report.verdict.value} (score {report.score}) -> "
              f"gate {'PASS' if ok else 'FAIL'}")
    return EXIT_OK if ok else EXIT_FAIL


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="songguard",
        description="Zero-dependency lyric copyright-infringement screener.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser(
        "screen",
        help="Screen a lyric file (or - for stdin) against a reference file/dir.",
    )
    sp.add_argument("input", help="input lyric file, or - for stdin")
    sp.add_argument("reference", help="reference lyric file or directory")
    sp.add_argument("--json", action="store_true", help="emit JSON")
    sp.set_defaults(func=cmd_screen)

    ck = sub.add_parser(
        "check",
        help="CI gate: exit 1 on any non-CLEAR verdict or score >= threshold.",
    )
    ck.add_argument("input", help="input lyric file, or - for stdin")
    ck.add_argument("reference", help="reference lyric file or directory")
    ck.add_argument("--json", action="store_true", help="emit JSON")
    ck.add_argument("--threshold", type=int, default=_THRESHOLD_DEFAULT,
                    help=f"score gate (default {_THRESHOLD_DEFAULT})")
    ck.set_defaults(func=cmd_check)

    return p


def main(argv: List[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except SongguardError as e:
        print(f"songguard: {e}", file=sys.stderr)
        return EXIT_ERROR
    except FileNotFoundError as e:
        print(f"songguard: file not found: {e}", file=sys.stderr)
        return EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main())