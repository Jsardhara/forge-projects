"""What the tracker row means for a version that is actually installed on this host.

The distinctions that matter, in order of how much they demand action:
``VULNERABLE_FIX_AVAILABLE`` (fix shipped, you are behind) beats ``VULNERABLE`` (no fix
information at all) beats ``VULNERABLE_PENDING_FIX`` (fix not built yet, wait) beats
``UNKNOWN`` (could not measure) beats ``PATCHED`` / ``IGNORED`` / ``NOT_IN_RELEASE``.
"""

from dataclasses import dataclass, field

from .tracker import rows_for_release
from .version import compare

RANK = {
    "VULNERABLE_FIX_AVAILABLE": 4,
    "VULNERABLE": 3,
    "VULNERABLE_PENDING_FIX": 2,
    "UNKNOWN": 1,
    "IGNORED": 0,
    "NOT_IN_RELEASE": 0,
    "PATCHED": 0,
}
VULNERABLE_VERDICTS = ("VULNERABLE", "VULNERABLE_FIX_AVAILABLE", "VULNERABLE_PENDING_FIX")


@dataclass(frozen=True)
class InstalledPackage:
    """One installed binary and the source package it was built from."""

    source: str
    binary: str
    version: str


@dataclass(frozen=True)
class RowResult:
    """The judgement for one installed binary against one tracker row."""

    source: str
    binary: str
    installed_version: str
    kind: str
    fixed_version: str
    released: bool
    verdict: str

    def render(self):
        if self.fixed_version:
            relation = ">=" if self.verdict == "PATCHED" else "<"
            return "%s %s %s %s -> %s" % (
                self.binary, self.installed_version, relation, self.fixed_version, self.verdict)
        return "%s %s (%s) -> %s" % (self.binary, self.installed_version, self.kind, self.verdict)


@dataclass(frozen=True)
class Assessment:
    """The worst verdict across every installed binary that maps to this CVE's rows."""

    cve_id: str
    release_id: str
    verdict: str
    fixed_version: str
    rows: tuple = field(default_factory=tuple)
    note: str = ""
    released: bool = False

    def vulnerable_rows(self):
        return [row for row in self.rows if row.verdict in VULNERABLE_VERDICTS]


def _judge(row, package):
    """Map one (row, installed binary) pair to a verdict."""
    if row.kind == "patched":
        verdict = "PATCHED"
    elif row.kind == "not_in_release":
        verdict = "NOT_IN_RELEASE"
    elif row.kind == "ignored":
        verdict = "IGNORED"
    elif row.kind == "pending":
        verdict = "VULNERABLE_PENDING_FIX"
    elif row.kind == "vulnerable":
        if not row.fixed_version:
            verdict = "VULNERABLE"
        elif compare(package.version, row.fixed_version) >= 0:
            verdict = "PATCHED"
        elif row.released:
            verdict = "VULNERABLE_FIX_AVAILABLE"
        else:
            verdict = "VULNERABLE_PENDING_FIX"
    else:
        verdict = "UNKNOWN"
    return RowResult(source=row.package, binary=package.binary,
                     installed_version=package.version, kind=row.kind,
                     fixed_version=row.fixed_version, released=row.released,
                     verdict=verdict)


def assess(page, release_id, codename, installed):
    """Assess one CVE page for one release and the installed packages on this host."""
    candidates = rows_for_release(page, release_id, codename)
    if not candidates:
        return Assessment(page.cve_id, release_id, "UNKNOWN", "", (),
                          "release %s is not present in the tracker page" % release_id)
    sources = {row.package for row in candidates}
    relevant = [package for package in installed if package.source in sources]
    if not relevant:
        return Assessment(
            page.cve_id, release_id, "UNKNOWN", "", (),
            "no installed package maps to a row source (%s) on release %s"
            % (", ".join(sorted(sources)), release_id))
    results = tuple(_judge(row, package)
                    for row in candidates
                    for package in relevant
                    if package.source == row.package)
    worst = max(results, key=lambda result: RANK[result.verdict])
    return Assessment(cve_id=page.cve_id, release_id=release_id, verdict=worst.verdict,
                      fixed_version=worst.fixed_version, rows=results,
                      released=worst.released)
