"""Per-CVE verdict. Two axes, kept apart on purpose.

``in_range`` answers "is the installed kernel below the fixed version" and is decided by
version comparison against a dated table. ``on_demonstrated_path`` answers "is the
demonstrated attack path reachable on this host" and is decided by measurement.

They are never merged into one verdict, for two reasons:

* **In range + no listener is still in range.** A host that is one service restart away
  from the path is not safe, and collapsing the axes would report it as such.
* **Not in range + listener is still exposure.** The listener set is a fact about the
  host, not a property of the CVE; it outlives this patch.

``UNKNOWN`` is a first-class verdict. It is returned when there is no verified fix row
for the running distro, or when the installed version cannot be read -- never silently
resolved to "patched", because "we could not compare" is exactly the state that hides a
vulnerable host.
"""

from dataclasses import dataclass
from typing import Optional, Tuple

from . import dpkgver, table

VULNERABLE = "vulnerable"
FIXED = "fixed"
NOT_AFFECTED = "not_affected"
UNKNOWN = "unknown"

REASON_NO_DISTRO_ROW = "no verified fix row for this distro"
REASON_NO_INSTALLED_VERSION = "installed kernel version could not be read"


@dataclass(frozen=True)
class Finding:
    cve: str
    title: str
    cvss: float
    vector: str
    verdict: str
    in_range: Optional[bool]
    on_demonstrated_path: Optional[bool]
    fix_state: Optional[str]
    installed_version: Optional[str]
    installed_package: Optional[str]
    running_release: Optional[str]
    fixed_version: Optional[str]
    abi_gap: Optional[int]
    exposure_surface: Tuple[str, ...]
    mptcp_enabled: Optional[bool]
    listener_count: Optional[int]
    source_url: Optional[str]
    retrieved_at: Optional[str]
    provenance_age_days: Optional[int]
    provenance_stale: bool
    attack_path_label: str
    attack_probe: str
    mitigation: dict
    reason: Optional[str] = None

    @property
    def measurable(self):
        return self.verdict != UNKNOWN


def installed_version_for(facts):
    """Package version when the DB has it; ``uname -r`` stripped of flavour otherwise.

    The package DB is authoritative -- it carries the ``-38.38`` ABI suffix that makes
    the comparison exact. The uname fallback is lossy and is flagged by the caller as
    such via ``reason`` only when it is all we have.
    """
    if facts.package_version:
        return facts.package_version
    if facts.release:
        return dpkgver.release_to_version(facts.release)
    return None


def on_path(facts):
    """True / False / None. None means a listener probe could not be read."""
    listeners = facts.mptcp_listeners
    if listeners is None:
        return None
    if facts.mptcp_enabled is False:
        return False
    return bool(len(listeners) > 0)


def _verdict_for(row, installed):
    if row.fix_state == table.FIX_NOT_AFFECTED:
        return NOT_AFFECTED, False
    if row.fix_state == table.FIX_PENDING:
        # The range is confirmed by the vendor and there is nothing to compare against
        # yet. That is a finding, not an "unmeasurable".
        return VULNERABLE, True
    below = dpkgver.compare(installed, row.fixed_version) < 0
    return (VULNERABLE if below else FIXED), below


def _base(cve, facts, installed, path):
    """The fields every finding carries, whatever the verdict turns out to be."""
    return {
        "cve": cve.cve,
        "title": cve.title,
        "cvss": cve.cvss,
        "vector": cve.vector,
        "on_demonstrated_path": path,
        "installed_version": installed,
        "installed_package": facts.package_name,
        "running_release": facts.release,
        "exposure_surface": facts.exposure_surface,
        "mptcp_enabled": facts.mptcp_enabled,
        "listener_count": (len(facts.mptcp_listeners)
                           if facts.mptcp_listeners is not None else None),
        "attack_path_label": cve.attack_path.label,
        "attack_probe": cve.attack_path.probe,
        "mitigation": dict(cve.mitigation),
    }


def assess_cve(cve, facts, now=None, stale_after_days=7):
    """One finding for one CVE against measured facts."""
    key = table.distro_key(facts.distro, facts.distro_release)
    row = cve.distros.get(key) if key else None
    installed = installed_version_for(facts)
    base = _base(cve, facts, installed, on_path(facts))

    if row is None:
        return Finding(
            verdict=UNKNOWN, in_range=None, fix_state=None, fixed_version=None,
            source_url=None, retrieved_at=None, provenance_age_days=None,
            provenance_stale=True, abi_gap=None,
            reason=REASON_NO_DISTRO_ROW, **base)

    age = table.age_days(row.retrieved_at, now)
    provenance = {
        "fix_state": row.fix_state,
        "fixed_version": row.fixed_version,
        "source_url": row.source_url,
        "retrieved_at": row.retrieved_at,
        "provenance_age_days": age,
        "provenance_stale": table.is_stale(age, stale_after_days),
    }

    if installed is None:
        return Finding(verdict=UNKNOWN, in_range=None, abi_gap=None,
                       reason=REASON_NO_INSTALLED_VERSION, **base, **provenance)

    verdict, in_range = _verdict_for(row, installed)
    try:
        gap = dpkgver.abi_gap(installed, row.fixed_version)
    except dpkgver.VersionError:
        gap = None

    return Finding(verdict=verdict, in_range=in_range, abi_gap=gap, **base, **provenance)


def exit_code(findings):
    """0 clean / 1 findings / 2 unmeasurable.

    ``in_range`` is the axis that pins the code. ``on_demonstrated_path`` is reported
    always and never pins it on its own, for the reason exitpath learned the hard way: a
    gate that is permanently red is a gate that gets switched off. A patched host that is
    still listening is exit 0 *with the listener printed*, not exit 1 forever.

    Precedence 1 > 2 is deliberate: a real range hit must be stated even when another
    CVE in the table could not be measured, otherwise the measurement problem hides the
    finding.
    """
    findings = tuple(findings)
    if any(f.in_range is True for f in findings):
        return 1
    if not findings or any(f.verdict == UNKNOWN for f in findings):
        return 2
    return 0
