"""Command line. Exit contract: 0 nothing to do / 1 a CVE still applies / 2 unmeasurable.

Exit 2 is mandatory whenever the tool could not measure - a missing release row, a failed
fetch, an unreadable host. "Could not measure" is never reported as "clean": that is the
failure mode that makes a watcher worse than no watcher.
"""

import argparse
import json
import sys
from datetime import datetime, timezone

from . import __version__, fetch, host, state, tracker, verdict
from .tracker import CVE_RE

PROG = "cvewatch"
EXIT_CLEAN, EXIT_VULNERABLE, EXIT_UNMEASURABLE = 0, 1, 2
TRACKER_URL = "https://ubuntu.com/security/%s"


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_parser():
    parser = argparse.ArgumentParser(
        prog=PROG,
        description="Watch a Ubuntu CVE tracker page and report when THIS host leaves the "
                    "affected range. Read-only, keyless, stdlib only. Exit 0 = patched / not "
                    "applicable, 1 = still vulnerable, 2 = could not measure.")
    parser.add_argument("--version", action="version", version="%s %s" % (PROG, __version__))
    parser.add_argument("--cve", action="append", default=[], metavar="CVE-ID",
                        help="CVE id to watch (repeatable)")
    parser.add_argument("--cve-file", metavar="PATH",
                        help="file of CVE ids, one per line, # comments ignored")
    parser.add_argument("--page", metavar="PATH",
                        help="read a saved tracker page instead of fetching (offline; one CVE)")
    parser.add_argument("--state", default="cvewatch-state.json", metavar="PATH",
                        help="state file to diff against (default: %(default)s)")
    parser.add_argument("--json", action="store_true", help="emit the machine-readable report")
    parser.add_argument("--quiet", action="store_true", help="print nothing; exit code only")
    parser.add_argument("--diff", action="store_true",
                        help="print transitions against the previous run's state")
    parser.add_argument("--timeout", type=int, default=20, help="fetch timeout in seconds")
    parser.add_argument("--release", default="", help="override the host's Ubuntu release id")
    parser.add_argument("--codename", default="", help="override the host's release codename")
    parser.add_argument("--installed", action="append", default=[], metavar="PKG=VERSION",
                        help="override the host's installed packages; SOURCE:PKG=VERSION is "
                             "accepted when the source package is not 'linux'")
    parser.add_argument("--no-host", action="store_true",
                        help="do not probe the host at all (requires --release/--installed)")
    parser.add_argument("--no-save", action="store_true", help="do not write the state file")
    return parser


def _cve_ids(args):
    """Requested CVE ids, in order, deduplicated. Raises ValueError on a malformed id."""
    found = []
    for item in args.cve or []:
        found.append(item.strip())
    if args.cve_file:
        try:
            with open(args.cve_file, encoding="utf-8") as handle:
                for line in handle:
                    text = line.split("#", 1)[0].strip()
                    if text:
                        found.append(text)
        except OSError as error:
            raise ValueError("cannot read --cve-file: %s" % error)
    unique = []
    for item in found:
        upper = item.upper()
        if not upper:
            continue
        if not CVE_RE.fullmatch(upper):
            raise ValueError("not a CVE id: %r" % item)
        if upper not in unique:
            unique.append(upper)
    return unique


def _parse_installed(tokens):
    """Parse ``[SOURCE:]PKG=VERSION`` overrides into InstalledPackage values."""
    packages = []
    for token in tokens:
        left, separator, version = token.rpartition("=")
        if not separator or not left or not version:
            raise ValueError("--installed needs PKG=VERSION, got %r" % token)
        source, separator, binary = left.rpartition(":")
        if not separator:
            source, binary = "linux", left
        packages.append(verdict.InstalledPackage(source=source.strip(), binary=binary.strip(),
                                                 version=version.strip()))
    return packages


def _collect_host(args):
    """Return (host_facts, installed, errors). --no-host skips every probe."""
    if args.no_host:
        facts = host.HostFacts("", "", ())
    else:
        facts = host.facts()
    installed = _parse_installed(args.installed) if args.installed else list(facts.installed)
    return facts, installed, list(facts.errors)


def _assess_one(cve, args, release_id, codename, installed):
    """Fetch/parse/assess one CVE. Any failure is UNKNOWN, never PATCHED."""
    source = args.page or (TRACKER_URL % cve)
    try:
        if args.page:
            with open(args.page, encoding="utf-8", errors="replace") as handle:
                text = handle.read()
        else:
            text = fetch.fetch(source, timeout=args.timeout)
    except (OSError, fetch.FetchError) as error:
        return verdict.Assessment(cve, release_id, "UNKNOWN", "", (), "cannot read page: %s" % error)
    page = tracker.parse(text, source=source)
    if page.cve_id and page.cve_id.upper() != cve:
        return verdict.Assessment(cve, release_id, "UNKNOWN", "", (),
                                  "page is for %s, not %s" % (page.cve_id, cve))
    return verdict.assess(page, release_id, codename, installed)


def _document(assessments, transitions, release_id, codename):
    return {
        "generated_at": _now(),
        "release": release_id,
        "codename": codename,
        "results": [
            {
                "cve": item.cve_id,
                "release": item.release_id,
                "verdict": item.verdict,
                "fixed_version": item.fixed_version,
                "released": item.released,
                "note": item.note,
                "rows": [
                    {"source": row.source, "binary": row.binary,
                     "installed_version": row.installed_version, "kind": row.kind,
                     "fixed_version": row.fixed_version, "released": row.released,
                     "verdict": row.verdict}
                    for row in item.rows
                ],
            }
            for item in assessments
        ],
        "transitions": [
            {"kind": item.kind, "cve": item.cve, "before": item.before, "after": item.after}
            for item in transitions
        ],
    }


def _render(document):
    lines = ["%s %s  Ubuntu %s%s" % (
        PROG, document["generated_at"], document["release"],
        " (%s)" % document["codename"] if document["codename"] else "")]
    for result in document["results"]:
        target = ""
        if result["fixed_version"]:
            target = "  fix target %s%s" % (
                result["fixed_version"], "" if result["released"] else " (not released)")
        lines.append("%s  %s%s" % (result["cve"], result["verdict"], target))
        if result["note"]:
            lines.append("  note: %s" % result["note"])
        for row in result["rows"]:
            relation = ">=" if row["verdict"] == "PATCHED" else "<"
            if row["fixed_version"]:
                lines.append("  %s %s %s %s -> %s" % (
                    row["binary"], row["installed_version"], relation,
                    row["fixed_version"], row["verdict"]))
            else:
                lines.append("  %s %s (%s) -> %s" % (
                    row["binary"], row["installed_version"], row["kind"], row["verdict"]))
    if document["transitions"]:
        lines.append("TRANSITIONS (%d)" % len(document["transitions"]))
        for transition in document["transitions"]:
            lines.append("  %s: %s (%s -> %s)" % (
                transition["cve"], transition["kind"], transition["before"] or "none",
                transition["after"] or "none"))
    vulnerable = [r for r in document["results"]
                  if r["verdict"] in verdict.VULNERABLE_VERDICTS]
    unmeasurable = [r for r in document["results"] if r["verdict"] == "UNKNOWN"]
    lines.append("verdict: %s" % (
        "%d CVE(s) still apply" % len(vulnerable) if vulnerable
        else "no CVE applies" if not unmeasurable else "nothing measurable"))
    if unmeasurable:
        lines.append("  %d CVE(s) unmeasurable" % len(unmeasurable))
    return "\n".join(lines)


def _exit_code(assessments):
    if any(item.verdict in verdict.VULNERABLE_VERDICTS for item in assessments):
        return EXIT_VULNERABLE
    if any(item.verdict == "UNKNOWN" for item in assessments):
        return EXIT_UNMEASURABLE
    return EXIT_CLEAN


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        cves = _cve_ids(args)
        facts, installed, host_errors = _collect_host(args)
        installed = installed
    except ValueError as error:
        sys.stderr.write("%s: %s\n" % (PROG, error))
        return EXIT_UNMEASURABLE

    if not cves:
        sys.stderr.write("%s: no CVE id given (--cve or --cve-file)\n" % PROG)
        return EXIT_UNMEASURABLE
    if args.page and len(cves) > 1:
        sys.stderr.write("%s: --page holds one CVE page; pass one --cve with it\n" % PROG)
        return EXIT_UNMEASURABLE

    release_id = args.release or facts.release_id
    codename = args.codename or facts.codename
    if not release_id and not codename:
        sys.stderr.write("%s: cannot determine this host's Ubuntu release "
                         "(pass --release or --codename)\n" % PROG)
        return EXIT_UNMEASURABLE

    previous = state.load(args.state)
    assessments = []
    current = {}
    for cve in cves:
        result = _assess_one(cve, args, release_id, codename, installed)
        assessments.append(result)
        current[cve] = state.snapshot(
            verdict=result.verdict, fixed_version=result.fixed_version,
            release=release_id,
            installed=[[row.binary, row.installed_version] for row in result.rows])

    transitions = state.diff(previous, current) if args.diff else []
    document = _document(assessments, transitions, release_id, codename)
    document["exit_code"] = _exit_code(assessments)
    document["host_errors"] = host_errors

    if not args.no_save:
        state.save(args.state, current)
    if not args.quiet:
        if args.json:
            print(json.dumps(document, indent=2, sort_keys=True))
        else:
            print(_render(document))
            if not args.no_save:
                print("state: %s" % args.state)
    return document["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
