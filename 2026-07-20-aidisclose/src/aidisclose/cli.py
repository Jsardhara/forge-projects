"""Command-line interface for aidisclose."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from typing import Optional

from .engine import analyze
from .models import OrgProfile
from .report import to_json, to_markdown
from .rules import load_mandates


def _parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


def _profile_from_path(path: str) -> OrgProfile:
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    return OrgProfile(
        name=str(data.get("name", "unnamed")),
        sectors=tuple(data.get("sectors", ())),
        jurisdictions=tuple(data.get("jurisdictions", ())),
        ai_uses=tuple(data.get("ai_uses", ())),
        implemented=tuple(data.get("implemented", ())),
        reference_date=_parse_date(data.get("reference_date")),
    )


def _profile_from_flags(args) -> OrgProfile:
    def _split(v):
        return tuple(x.strip() for x in v.split(",") if x.strip()) if v else ()
    return OrgProfile(
        name=args.name or "unnamed",
        sectors=_split(args.sectors),
        jurisdictions=_split(args.jurisdictions),
        ai_uses=_split(args.ai_uses),
        implemented=_split(args.implemented),
        reference_date=_parse_date(args.reference_date),
    )


def _build_profile(args) -> OrgProfile:
    if getattr(args, "profile", None):
        return _profile_from_path(args.profile)
    return _profile_from_flags(args)


def cmd_list(args) -> int:
    mandates = load_mandates()
    if args.status:
        targets = {s.lower() for s in args.status.split(",")}
        mandates = tuple(m for m in mandates if m.status.value in targets)
    for m in mandates:
        eff = m.effective_date.isoformat() if m.effective_date else "-"
        print(f"{m.mid:18s} {m.jurisdiction:8s} {m.status.value:10s} "
              f"{eff:12s} {m.title}")
    print(f"\n{len(mandates)} mandate(s).")
    return 0


def cmd_analyze(args) -> int:
    profile = _build_profile(args)
    report = analyze(profile)
    if args.format == "json":
        print(to_json(report))
    else:
        print(to_markdown(report))
    return 0


def cmd_check(args) -> int:
    profile = _build_profile(args)
    report = analyze(profile)
    if args.format == "json":
        print(to_json(report))
    else:
        print(to_markdown(report))
    # CI gate: non-zero when a blocking (critical) disclosure gap exists.
    return 1 if report.blocking else 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="aidisclose",
        description="AI-disclosure compliance gap analyzer.")
    sub = p.add_subparsers(dest="command", required=True)

    pl = sub.add_parser("list", help="List tracked mandates.")
    pl.add_argument("--status", help="Comma-separated status filter.")
    pl.set_defaults(func=cmd_list)

    pa = sub.add_parser("analyze", help="Analyze an org profile.")
    _add_profile_args(pa)
    pa.add_argument("--format", choices=("md", "json"), default="md")
    pa.set_defaults(func=cmd_analyze)

    pc = sub.add_parser("check", help="CI gate: exit 1 if blocking gaps.")
    _add_profile_args(pc)
    pc.add_argument("--format", choices=("md", "json"), default="md")
    pc.set_defaults(func=cmd_check)

    return p


def _add_profile_args(pa):
    pa.add_argument("--profile", help="Path to a JSON org profile.")
    pa.add_argument("--name", help="Org name (flag mode).")
    pa.add_argument("--sectors", help="Comma-separated sectors.")
    pa.add_argument("--jurisdictions", help="Comma-separated jurisdictions.")
    pa.add_argument("--ai_uses", "--uses", dest="ai_uses",
                    help="Comma-separated AI use cases.")
    pa.add_argument("--implemented", help="Comma-separated obligation codes met.")
    pa.add_argument("--reference-date", dest="reference_date",
                    help="YYYY-MM-DD reference date (default: today).")


def main(argv: Optional[list] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
