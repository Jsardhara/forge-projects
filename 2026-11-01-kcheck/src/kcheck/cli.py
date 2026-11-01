"""Command line. Exit contract: 0 clean / 1 findings / 2 unmeasurable.

``--json`` emits the same document ``render_text`` formats, so a cron consumer and a
human see one source of truth. ``--fixtures DIR`` replays recorded probe transcripts
instead of running anything, which is how the tests exercise this code path without
depending on the kernel the test happens to run under.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

from . import assess, host, report, table

PROG = "kcheck"


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_parser():
    parser = argparse.ArgumentParser(
        prog=PROG,
        description=("Report whether THIS host's installed kernel is in the affected range of a "
                     "known kernel CVE, and whether the demonstrated attack path is reachable. "
                     "Read-only, offline, no root, no network."))
    parser.add_argument("--json", action="store_true", help="emit the machine-readable report")
    parser.add_argument("--quiet", action="store_true", help="print nothing; exit code only")
    parser.add_argument("--fixtures", metavar="DIR",
                        help="replay probe transcripts from DIR instead of running probes "
                             "(files: uname.txt, dpkg.txt, sysctl.txt, ss.txt, os-release.txt)")
    parser.add_argument("--table", default=table.DEFAULT_PATH,
                        help="fix table to use (default: %s)" % table.DEFAULT_PATH)
    parser.add_argument("--cve", default="",
                        help="comma-separated CVE ids to check (default: every row in the table)")
    return parser


def _select(table_doc, wanted):
    if not wanted:
        return table_doc.cves
    keep = {token.strip().upper() for token in wanted.split(",") if token.strip()}
    return tuple(cve for cve in table_doc.cves if cve.cve.upper() in keep)


def _collect(fixtures):
    """Probe the host. Returns (facts, fatal_message_or_None)."""
    facts = host.gather(fixtures=fixtures)
    if facts.release or facts.distro:
        return facts, None
    detail = "; ".join(facts.errors) or "no probe returned anything"
    return facts, "cannot collect host probes: %s" % detail


def _resolve_table(args):
    """Explicit --table wins; else a fixture-provided table.json; else the shipped table."""
    if args.table != table.DEFAULT_PATH:
        return args.table
    if args.fixtures:
        candidate = os.path.join(args.fixtures, "table.json")
        if os.path.isfile(candidate):
            return candidate
    return args.table


def main(argv=None):
    args = build_parser().parse_args(argv)

    try:
        table_doc = table.load(_resolve_table(args))
    except table.TableError as exc:
        # A missing or malformed table is unmeasurable, never a clean bill of health.
        print("%s: %s" % (PROG, exc), file=sys.stderr)
        return 2

    facts, fatal = _collect(args.fixtures)
    if fatal:
        print("%s: %s" % (PROG, fatal), file=sys.stderr)
        return 2

    selected = _select(table_doc, args.cve)
    if not selected:
        print("%s: no CVE in %s matches %r" % (PROG, table_doc.path, args.cve), file=sys.stderr)
        return 2

    findings = tuple(assess.assess_cve(cve, facts, stale_after_days=table_doc.stale_after_days)
                     for cve in selected)
    doc = report.build_report(findings, facts, table_doc, _now())

    if not args.quiet:
        if args.json:
            sys.stdout.write(json.dumps(doc, indent=2, sort_keys=True) + "\n")
        else:
            sys.stdout.write(report.render_text(doc))
    return doc["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
