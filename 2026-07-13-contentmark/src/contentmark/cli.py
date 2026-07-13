"""Command-line interface for contentmark.

Subcommands:
  detect     — analyze text on stdin/path for AI-content signals (exit 1 if very_likely_ai)
  label      — embed provenance marker + invisible signature into text
  verify     — check provenance marker in text
  badge      — emit the disclosure badge HTML/JS/CSS spec
  explain    — print the detection report in human-readable form
"""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone

from .badge import badge_css, badge_html, badge_script, band_label
from .detector import detect
from .models import Provenance, ProvenanceLabel
from .watermark import embed, verify


def _read_text(path: str | None) -> str:
    if path == "-" or path is None:
        return sys.stdin.read()
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def _cmd_detect(args: argparse.Namespace) -> int:
    text = _read_text(args.file)
    report = detect(text)
    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(report.explain())
    return 1 if report.band.value == "very_likely_ai" else 0


def _cmd_explain(args: argparse.Namespace) -> int:
    text = _read_text(args.file)
    report = detect(text)
    print(report.explain())
    return 0


def _cmd_label(args: argparse.Namespace) -> int:
    text = _read_text(args.file)
    try:
        label = ProvenanceLabel(args.label)
    except ValueError:
        print(f"error: invalid label {args.label!r}", file=sys.stderr)
        return 2
    rid = args.rid or f"cm_{uuid.uuid4().hex[:12]}"
    prov = Provenance(
        rid=rid,
        label=label,
        tool=args.tool,
        model=args.model,
        author=args.author,
        note=args.note,
        generated_at=datetime.now(timezone.utc),
    )
    out = embed(text, prov)
    if args.inline:
        sys.stdout.write(out)
    else:
        print(out)
    return 0


def _cmd_verify(args: argparse.Namespace) -> int:
    text = _read_text(args.file)
    result = verify(text)
    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(
            f"present={result.present} valid={result.valid} tampered={result.tampered} "
            f"label={result.label} rid={result.rid}\n  {result.detail}"
        )
    if result.tampered:
        return 1
    return 0


def _cmd_badge(args: argparse.Namespace) -> int:
    label = ProvenanceLabel(args.label)
    rid = args.rid or f"cm_{uuid.uuid4().hex[:12]}"
    prov = Provenance(rid=rid, label=label, tool=args.tool, model=args.model, author=args.author)
    if args.part == "html":
        print(badge_html(prov, compact=args.compact))
    elif args.part == "css":
        print(badge_css())
    elif args.part == "js":
        print(badge_script())
    elif args.part == "all":
        print("<!-- contentmark disclosure badge -->")
        print("<style>")
        print(badge_css())
        print("</style>")
        print(badge_html(prov, compact=args.compact))
        print("<script>")
        print(badge_script())
        print("</script>")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="contentmark", description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="command", required=True)

    pd = sub.add_parser("detect", help="detect AI-content signals")
    pd.add_argument("file", nargs="?", default="-", help="file path or - for stdin")
    pd.add_argument("--json", action="store_true", help="emit JSON")
    pd.set_defaults(func=_cmd_detect)

    pe = sub.add_parser("explain", help="human-readable explanation")
    pe.add_argument("file", nargs="?", default="-")
    pe.set_defaults(func=_cmd_explain)

    pl = sub.add_parser("label", help="embed provenance + signature")
    pl.add_argument("file", nargs="?", default="-")
    pl.add_argument("--label", required=True, choices=[l.value for l in ProvenanceLabel])
    pl.add_argument("--rid", default=None)
    pl.add_argument("--tool", default=None)
    pl.add_argument("--model", default=None)
    pl.add_argument("--author", default=None)
    pl.add_argument("--note", default=None)
    pl.add_argument("--inline", action="store_true", help="no trailing newline")
    pl.set_defaults(func=_cmd_label)

    pv = sub.add_parser("verify", help="verify provenance marker")
    pv.add_argument("file", nargs="?", default="-")
    pv.add_argument("--json", action="store_true")
    pv.set_defaults(func=_cmd_verify)

    pb = sub.add_parser("badge", help="emit disclosure badge spec")
    pb.add_argument("--label", required=True, choices=[l.value for l in ProvenanceLabel])
    pb.add_argument("--rid", default=None)
    pb.add_argument("--tool", default=None)
    pb.add_argument("--model", default=None)
    pb.add_argument("--author", default=None)
    pb.add_argument("--part", choices=["html", "css", "js", "all"], default="all")
    pb.add_argument("--compact", action="store_true")
    pb.set_defaults(func=_cmd_badge)

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)
