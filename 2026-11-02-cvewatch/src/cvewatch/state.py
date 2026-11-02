"""Previous-run state and the transitions between runs.

The contract: a run whose state did not change produces zero transitions, so a cron can
alert on "transitions is non-empty" and stay silent for the months a fix takes to ship.
"""

import json
import os
import tempfile
from dataclasses import dataclass

STATE_VERSION = 1


def snapshot(verdict, fixed_version, release, installed):
    """Build one state entry. ``installed`` is a list of [binary, version] pairs."""
    return {
        "verdict": verdict,
        "fixed_version": fixed_version or "",
        "release": release,
        "installed": sorted([list(pair) for pair in installed]),
    }


def load(path):
    """Load a state document; missing or corrupt means 'no previous run', never a crash."""
    try:
        with open(path, encoding="utf-8") as handle:
            document = json.load(handle)
    except (OSError, ValueError):
        return {}
    if not isinstance(document, dict):
        return {}
    entries = document.get("cves", document)
    if not isinstance(entries, dict):
        return {}
    return {key: value for key, value in entries.items() if isinstance(value, dict)}


def save(path, entries):
    """Write atomically: a half-written state file would look like a kernel change."""
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    document = {"version": STATE_VERSION, "cves": entries}
    handle = tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=directory, delete=False, suffix=".tmp")
    try:
        json.dump(document, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    finally:
        handle.close()
    os.replace(handle.name, path)


@dataclass(frozen=True)
class Transition:
    kind: str
    cve: str
    before: str
    after: str

    def render(self):
        return "%s: %s (%s -> %s)" % (self.cve, self.kind, self.before or "none",
                                      self.after or "none")


def _installed(entry):
    pairs = entry.get("installed") or []
    return sorted(tuple(pair) for pair in pairs if isinstance(pair, (list, tuple)))


def diff(previous, current):
    """Return every transition between two state documents. Empty means 'nothing to say'."""
    transitions = []
    for cve in sorted(current):
        now = current[cve]
        before = previous.get(cve)
        if before is None:
            transitions.append(Transition("new_cve", cve, "", str(now.get("verdict", ""))))
            continue
        if before.get("verdict") != now.get("verdict"):
            transitions.append(Transition("verdict_changed", cve,
                                          str(before.get("verdict", "")),
                                          str(now.get("verdict", ""))))
        if (before.get("fixed_version") or "") != (now.get("fixed_version") or ""):
            transitions.append(Transition("target_version_changed", cve,
                                          str(before.get("fixed_version") or ""),
                                          str(now.get("fixed_version") or "")))
        if _installed(before) != _installed(now):
            transitions.append(Transition("kernel_changed", cve,
                                          ", ".join("%s=%s" % pair for pair in _installed(before)),
                                          ", ".join("%s=%s" % pair for pair in _installed(now))))
    return transitions
