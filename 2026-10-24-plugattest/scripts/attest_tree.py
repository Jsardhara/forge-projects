"""Attest every skill package in a tree. Real-world corpus runner.

Usage: PYTHONPATH=src python3 scripts/attest_tree.py <tree-root>

Each immediate-and-nested directory containing a SKILL.md, package.json or
plugin.json is treated as one package.
"""

import os
import sys

from plugattest.attest import attest

MARKERS = ("SKILL.md", "package.json", "plugin.json")


def find_packages(root):
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in {".git", "node_modules", "_trash"})
        if any(marker in filenames for marker in MARKERS):
            found.append(dirpath)
    return found


def main(argv):
    if len(argv) != 2:
        print("usage: attest_tree.py <tree-root>", file=sys.stderr)
        return 2
    root = argv[1]
    if not os.path.isdir(root):
        print("error: not a directory: %s" % root, file=sys.stderr)
        return 2

    packages = find_packages(root)
    tallies = {"PASS": 0, "INFO": 0, "WARN": 0, "FLAG": 0}
    flagged = []
    for path in packages:
        report = attest(path)
        tallies[report.verdict.value] += 1
        if report.verdict.value in ("WARN", "FLAG"):
            codes = sorted({f.code for f in report.findings})
            flagged.append((report.package, report.verdict.value, ",".join(codes),
                            ",".join(report.detected) or "-"))

    print("packages attested: %d" % len(packages))
    for verdict in ("PASS", "INFO", "WARN", "FLAG"):
        print("  %-4s %d" % (verdict, tallies[verdict]))
    print()
    print("%-38s %-5s %-18s %s" % ("PACKAGE", "VERD", "CODES", "DETECTED"))
    for row in flagged:
        print("%-38s %-5s %-18s %s" % row)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
