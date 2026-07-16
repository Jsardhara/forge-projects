"""Command-line interface for tokenaudit."""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Dict, List, Optional

from .models import CostReport
from .parse import parse_session, parse_session_text
from .pricing import DEFAULT_PRICING, load_prices
from .report import build_report


def _load_pricing(path: Optional[str]) -> Dict:
    if path:
        return load_prices(path)
    return DEFAULT_PRICING


def render_md(report: CostReport) -> str:
    lines: List[str] = []
    lines.append(f"# Token Audit: {os.path.basename(report.session)}")
    lines.append("")
    lines.append(f"- **Agent:** {report.agent}")
    lines.append(
        f"- **Tokens:** {report.total_input:,} in / {report.total_output:,} out"
    )
    lines.append(f"- **Estimated cost:** ${report.total_cost:,.4f}")
    if report.wasted_tokens:
        lines.append(
            f"- **Est. recoverable:** {report.wasted_tokens:,} tokens "
            f"(~${report.wasted_cost:,.4f})"
        )
    lines.append("")
    lines.append("## Phase breakdown")
    lines.append("")
    lines.append("| Phase | Tokens |")
    lines.append("| --- | --- |")
    lines.append(f"| Pre-read (before 1st tool) | {report.phase.preread_input:,} |")
    lines.append(f"| Tool results | {report.phase.tool_result_input:,} |")
    lines.append(f"| Other input | {report.phase.other_input:,} |")
    lines.append(f"| Generation (output) | {report.phase.generation_output:,} |")
    lines.append("")
    if report.findings:
        lines.append("## Waste findings")
        lines.append("")
        for f in report.findings:
            lines.append(f"- **[{f.severity}] {f.kind}**: {f.detail}")
        lines.append("")
    if report.file_reads:
        lines.append("## File reads (top 10)")
        lines.append("")
        lines.append("| File | Reads | Est. tokens |")
        lines.append("| --- | --- | --- |")
        for fr in report.file_reads[:10]:
            lines.append(f"| `{fr.path}` | {fr.read_count} | {fr.est_input_tokens:,} |")
        lines.append("")
    if report.recommendations:
        lines.append("## Recommendations")
        lines.append("")
        for r in report.recommendations:
            pct = (
                f" (save ~{r.potential_savings_pct * 100:.0f}%)"
                if r.potential_savings_pct is not None
                else ""
            )
            lines.append(f"- **{r.title}**{pct}: {r.detail}")
        lines.append("")
    return "\n".join(lines)


def render_json(report: CostReport) -> str:
    return json.dumps(report.as_dict(), indent=2)


def render_compare(a: CostReport, b: CostReport, name_a: str = "A",
                   name_b: str = "B") -> str:
    rows = [
        ("Agent", a.agent, b.agent),
        ("Cost ($)", f"{a.total_cost:,.4f}", f"{b.total_cost:,.4f}"),
        ("Input tokens", f"{a.total_input:,}", f"{b.total_input:,}"),
        ("Output tokens", f"{a.total_output:,}", f"{b.total_output:,}"),
        ("Pre-read input", f"{a.phase.preread_input:,}", f"{b.phase.preread_input:,}"),
        ("Tool-result input", f"{a.phase.tool_result_input:,}", f"{b.phase.tool_result_input:,}"),
        ("Waste findings", str(len(a.findings)), str(len(b.findings))),
        ("Recoverable tokens", f"{a.wasted_tokens:,}", f"{b.wasted_tokens:,}"),
    ]
    out = ["# Token Audit: Compare", ""]
    out.append(f"| Metric | {name_a} | {name_b} |")
    out.append("| --- | --- | --- |")
    for name, av, bv in rows:
        out.append(f"| {name} | {av} | {bv} |")
    out.append("")
    return "\n".join(out)


def cmd_profile(args: argparse.Namespace) -> int:
    table = _load_pricing(args.prices)
    session = parse_session(args.path)
    report = build_report(session, table)
    if args.format == "json":
        print(render_json(report))
    else:
        print(render_md(report))
    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    table = _load_pricing(args.prices)
    ra = build_report(parse_session(args.a), table)
    rb = build_report(parse_session(args.b), table)
    print(render_compare(ra, rb, os.path.basename(ra.session), os.path.basename(rb.session)))
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    table = _load_pricing(args.prices)
    files = sorted(
        f for f in os.listdir(args.dir)
        if f.endswith(".jsonl")
    )
    if not files:
        print(f"No .jsonl transcripts found in {args.dir}", file=sys.stderr)
        return 1
    print("# Token Audit: Batch Report\n")
    print("| Session | Agent | Cost ($) | Input | Output | Findings |")
    print("| --- | --- | --- | --- | --- | --- |")
    for f in files:
        path = os.path.join(args.dir, f)
        try:
            rep = build_report(parse_session(path), table)
        except Exception as e:  # noqa: BLE001
            print(f"| {f} | ERROR | {e} | | | |")
            continue
        print(
            f"| {f} | {rep.agent} | {rep.total_cost:,.4f} | "
            f"{rep.total_input:,} | {rep.total_output:,} | {len(rep.findings)} |"
        )
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="tokenaudit",
        description="Coding-agent token-cost profiler & efficiency auditor.",
    )
    sub = p.add_subparsers(dest="command", required=True)

    pp = sub.add_parser("profile", help="Profile a single transcript")
    pp.add_argument("path", help="Path to a .jsonl transcript")
    pp.add_argument("--format", choices=["md", "json"], default="md")
    pp.add_argument("--prices", default=None, help="JSON pricing override")
    pp.set_defaults(func=cmd_profile)

    pc = sub.add_parser("compare", help="Compare two transcripts side by side")
    pc.add_argument("a", help="First transcript")
    pc.add_argument("b", help="Second transcript")
    pc.add_argument("--prices", default=None)
    pc.set_defaults(func=cmd_compare)

    pr = sub.add_parser("report", help="Batch-profile all .jsonl in a directory")
    pr.add_argument("dir", help="Directory of .jsonl transcripts")
    pr.add_argument("--prices", default=None)
    pr.set_defaults(func=cmd_report)

    return p


def run_cli(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


def main() -> int:
    return run_cli()
