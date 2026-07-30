"""Command-line interface for vibecraft."""

import argparse
import json
import sys
from pathlib import Path

from vibecraft.scorer import score_craftsmanship


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="vibecraft",
        description="AI-Assisted Code Craftsmanship Auditor — detect vibe-coding patterns",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze a Python file")
    analyze_parser.add_argument("file", help="Path to Python file to analyze")
    analyze_parser.add_argument("--json", action="store_true", help="Output JSON")

    # check command (CI gate)
    check_parser = subparsers.add_parser("check", help="CI gate: exit 1 if below threshold")
    check_parser.add_argument("file", help="Path to Python file")
    check_parser.add_argument(
        "--threshold", type=float, default=70.0,
        help="Minimum acceptable score (default: 70.0)",
    )
    check_parser.add_argument("--json", action="store_true", help="Output JSON")

    args = parser.parse_args()

    if args.command == "analyze":
        return _analyze(args.file, args.json)
    elif args.command == "check":
        return _check(args.file, args.threshold, args.json)
    return 0


def _analyze(file_path: str, json_output: bool) -> int:
    try:
        source = Path(file_path).read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"vibecraft: error: file not found: {file_path}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"vibecraft: error reading file: {e}", file=sys.stderr)
        return 1

    report = score_craftsmanship(source, file_path)

    if json_output:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        _print_report(report)

    return 0


def _check(file_path: str, threshold: float, json_output: bool) -> int:
    try:
        source = Path(file_path).read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"vibecraft: error: file not found: {file_path}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"vibecraft: error reading file: {e}", file=sys.stderr)
        return 1

    report = score_craftsmanship(source, file_path)

    if json_output:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        _print_report(report)

    if report.score < threshold:
        print(f"\nvibecraft: CI GATE FAILED — score {report.score:.1f} < threshold {threshold:.1f}")
        return 1

    print(f"\nvibecraft: CI GATE PASSED — score {report.score:.1f} >= threshold {threshold:.1f}")
    return 0


def _print_report(report) -> None:
    grade_color = _grade_color(report.grade)
    band_color = _band_color(report.band())

    print(f"\n=== vibecraft report: {report.file_path} ===")
    print(f"  Score:      {grade_color}{report.score:.1f}{Style.RESET} / 100  [Grade: {grade_color}{report.grade}{Style.RESET}]")
    print(f"  Band:       {band_color}{report.band()}{Style.RESET}")
    print(f"  Lines:      {report.total_lines}")
    print(f"  Findings:   {report.finding_count}")
    print(f"  Doc:        {report.doc_coverage * 100:.0f}%  (functions with docstrings)")
    print(f"  Err-handl:  {report.error_handling_score * 100:.0f}%")
    print(f"  Complexity: {report.complexity_score * 100:.0f}%")
    print(f"  Naming:     {report.naming_score * 100:.0f}%")

    if report.findings:
        print(f"\n  Findings:")
        for f in report.findings:
            sev = f.severity.value.upper()
            sev_prefix = _severity_prefix(f.severity)
            print(f"    {sev_prefix}[{sev}] L{f.line}: {f.message}")


class Style:
    RESET = "\033[0m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    GREEN = "\033[92m"
    CYAN = "\033[96m"


def _grade_color(grade: str) -> str:
    if grade in ("A", "B"):
        return Style.GREEN
    elif grade == "C":
        return Style.YELLOW
    else:
        return Style.RED


def _band_color(band: str) -> str:
    if band == "excellent":
        return Style.GREEN
    elif band == "good":
        return Style.CYAN
    elif band == "fair":
        return Style.YELLOW
    else:
        return Style.RED


def _severity_prefix(severity) -> str:
    if severity == Severity.CRITICAL:
        return "\033[91m"
    elif severity == Severity.WARNING:
        return "\033[93m"
    else:
        return "\033[96m"


if __name__ == "__main__":
    sys.exit(main())
