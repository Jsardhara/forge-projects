"""Command line entry point: attest a plugin/skill package, gate on the verdict."""

import argparse
import json
import sys

from .attest import EXIT_CLEAN, EXIT_FINDINGS, EXIT_USAGE, attest
from .models import SEVERITY_RANK, Severity

GATE_CHOICES = ("none", "info", "warn", "flag")


def _build_parser():
    parser = argparse.ArgumentParser(
        prog="plugattest",
        description="Attest that a plugin/skill package only uses the capabilities "
                    "its manifest declares.",
    )
    parser.add_argument("path", help="package directory to attest")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    parser.add_argument("--fail-on", choices=GATE_CHOICES, default="warn",
                        help="lowest verdict that fails the gate (default: warn)")
    return parser


def _format_text(report):
    lines = [
        "plugattest: %s" % report.package,
        "  declared: %s" % (", ".join(report.declared) or "<none>"),
        "  detected: %s" % (", ".join(report.detected) or "<none>"),
        "  verdict:  %s (score %d/100)" % (report.verdict.value, report.score),
    ]
    for finding in report.findings:
        lines.append("  %s %-5s %s -- %s [%s]" % (
            finding.code, finding.severity.value, finding.location,
            finding.message, finding.capability or "-"))
    if not report.findings:
        lines.append("  no findings")
    return "\n".join(lines)


def _gate_failed(report, fail_on):
    if fail_on == "none":
        return False
    threshold = SEVERITY_RANK[Severity(fail_on.upper())]
    return SEVERITY_RANK[report.verdict] >= threshold


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:  # argparse already printed usage
        return EXIT_USAGE if exc.code else EXIT_CLEAN

    try:
        report = attest(args.path)
    except OSError as exc:
        print("error: %s" % exc)
        return EXIT_USAGE

    if args.json:
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    else:
        print(_format_text(report))

    return EXIT_FINDINGS if _gate_failed(report, args.fail_on) else EXIT_CLEAN
