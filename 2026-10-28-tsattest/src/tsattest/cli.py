"""Command line entry point. Exit contract: 0 clean, 1 at/above threshold, 2 cannot answer."""

import argparse
import sys

from . import collect, report


def build_parser():
    parser = argparse.ArgumentParser(
        prog="tsattest",
        description=("Report which Tailscale security bulletins apply to this node and "
                     "whether the SSH mitigation is loaded in the running process. "
                     "Read-only, offline, no network calls."))
    parser.add_argument("--json", action="store_true",
                        help="emit the report as JSON instead of prose")
    parser.add_argument("--fixtures", metavar="DIR",
                        help="read probe outputs from a fixture directory instead of "
                             "running tailscale (files: version.txt, prefs.json, "
                             "status.json, serve.txt, environ.txt, defaults.txt)")
    parser.add_argument("--tailscale-bin", default="tailscale",
                        help="path to the tailscale binary (default: tailscale)")
    parser.add_argument("--defaults-file", default=collect.DEFAULT_FILE,
                        help="systemd EnvironmentFile to read as the DECLARED value "
                             "(default: %s)" % collect.DEFAULT_FILE)
    parser.add_argument("--strict", action="store_true",
                        help="treat UNKNOWN as failure (exit 1) for CI gates")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        collected = collect.gather(fixtures=args.fixtures,
                                   tailscale_bin=args.tailscale_bin,
                                   defaults_file=args.defaults_file)
    except OSError as exc:
        print("tsattest: cannot collect probes: %s" % exc, file=sys.stderr)
        return 2
    doc = report.build_report(collected)
    print(report.render_json(doc) if args.json else report.render_plain(doc))
    code = doc["exit_code"]
    if args.strict and code == 2:
        code = 1
    return code
