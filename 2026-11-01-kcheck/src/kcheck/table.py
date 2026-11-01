"""The checked-in fix table: versioned data, validated at load, provenance-carrying.

Design notes that matter:

* **Validated at load, not at use.** A missing ``source_url`` or an unrecognised
  ``fix_state`` raises here, before any verdict is computed. The failure mode this
  prevents is the one that bit the v1 builder job: a path that did not exist, discovered
  at 06:15 by a silent failure instead of at load by a loud one.
* **Every row carries ``retrieved_at`` and ``source_url``.** A row that has aged out is
  still usable, but it must *say* it is old. Staleness is reported, not fatal -- making
  it fatal would pin the exit code at 2 forever and the gate would be ignored, which is
  how a security check becomes decoration.
* **Unknown is a value, not a default.** ``fix_state`` distinguishes ``pending`` (the
  vendor says the fix is not out yet) from ``released`` (there is a version to compare
  against). A distro with no row is *unknown*, and the caller must exit 2 -- it must
  never be read as "patched".
"""

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Mapping, Optional, Tuple

from . import dpkgver

FIX_PENDING = "pending"
FIX_RELEASED = "released"
FIX_NOT_AFFECTED = "not_affected"
FIX_STATES = (FIX_PENDING, FIX_RELEASED, FIX_NOT_AFFECTED)

SCHEMA_VERSION = 1

_TS_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


class TableError(Exception):
    """The table is missing, malformed, or missing provenance. Always fatal to a verdict."""


@dataclass(frozen=True)
class DistroRow:
    key: str
    distro: str
    release: str
    codename: str
    fix_state: str
    fixed_version: str
    status_text: str
    source_url: str
    retrieved_at: str


@dataclass(frozen=True)
class AttackPath:
    label: str
    probe: str


@dataclass(frozen=True)
class Cve:
    cve: str
    title: str
    cvss: float
    vector: str
    published: str
    introduced: str
    branches: Mapping[str, str]
    attack_path: AttackPath
    mitigation: Mapping[str, object]
    distros: Mapping[str, DistroRow]
    kev: bool = False
    exploited_in_wild: bool = False


@dataclass(frozen=True)
class Table:
    path: str
    schema_version: int
    generated_at: str
    stale_after_days: int
    cves: Tuple[Cve, ...] = field(default_factory=tuple)

    def get(self, cve_id):
        for cve in self.cves:
            if cve.cve == cve_id:
                return cve
        return None

    def for_distro(self, cve_id, distro_key):
        cve = self.get(cve_id)
        if cve is None or not distro_key:
            return None
        return cve.distros.get(distro_key)


def distro_key(distro, release):
    """``("ubuntu", "26.04")`` -> ``"ubuntu-26.04"``; no release -> ``"arch"``."""
    name = (distro or "").strip().lower()
    if not name:
        return ""
    version = (release or "").strip()
    return "%s-%s" % (name, version) if version else name


def _require(mapping, key, where):
    if key not in mapping:
        raise TableError("%s is missing required field %r" % (where, key))
    return mapping[key]


def _as_url(value, where):
    if not isinstance(value, str) or not value.startswith(("https://", "http://")):
        raise TableError("%s: source_url %r is not an http(s) URL -- provenance must be "
                         "checkable" % (where, value))
    return value


def _parse_row(key, raw):
    where = "distro row %r" % key
    if not isinstance(raw, dict):
        raise TableError("%s is not an object" % where)
    for required in ("distro", "release", "fix_state", "fixed_version", "source_url", "retrieved_at"):
        _require(raw, required, where)

    fix_state = raw["fix_state"]
    if fix_state not in FIX_STATES:
        raise TableError("%s: fix_state %r is not one of %s" % (where, fix_state, ", ".join(FIX_STATES)))

    fixed_version = str(raw["fixed_version"]).strip()
    if fix_state != FIX_NOT_AFFECTED:
        try:
            dpkgver.split_version(fixed_version)
        except dpkgver.VersionError as exc:
            raise TableError("%s: fixed_version %r is not a version: %s"
                             % (where, fixed_version, exc))

    retrieved_at = str(raw["retrieved_at"]).strip()
    if not parse_timestamp(retrieved_at):
        raise TableError("%s: retrieved_at %r is not an ISO-8601 Z timestamp"
                         % (where, retrieved_at))

    return DistroRow(
        key=key,
        distro=str(raw["distro"]).lower(),
        release=str(raw["release"]),
        codename=str(raw.get("codename", "")),
        fix_state=fix_state,
        fixed_version=fixed_version,
        status_text=str(raw.get("status_text", "")),
        source_url=_as_url(raw["source_url"], where),
        retrieved_at=retrieved_at,
    )


def _parse_cve(raw):
    where = "cve %r" % (raw.get("cve") if isinstance(raw, dict) else raw)
    if not isinstance(raw, dict):
        raise TableError("%s is not an object" % where)
    for required in ("cve", "title", "cvss", "cvss_vector", "attack_path", "mitigation",
                     "fixed_branches", "distros"):
        _require(raw, required, where)

    distros_raw = raw["distros"]
    if not isinstance(distros_raw, dict) or not distros_raw:
        raise TableError("%s has no distro rows" % where)
    distros = {key: _parse_row(key, value) for key, value in distros_raw.items()}

    path = raw["attack_path"]
    if not isinstance(path, dict) or not path.get("label") or not path.get("probe"):
        raise TableError("%s: attack_path needs both 'label' and 'probe'" % where)

    mitigation = raw["mitigation"]
    if not isinstance(mitigation, dict) or not mitigation.get("pointer"):
        raise TableError("%s: mitigation needs a 'pointer' (this tool never applies one)" % where)

    try:
        cvss = float(raw["cvss"])
    except (TypeError, ValueError):
        raise TableError("%s: cvss %r is not a number" % (where, raw["cvss"]))

    return Cve(
        cve=str(raw["cve"]),
        title=str(raw["title"]),
        cvss=cvss,
        vector=str(raw["cvss_vector"]),
        published=str(raw.get("published", "")),
        introduced=str(raw.get("introduced", "")),
        branches={str(k): str(v) for k, v in dict(raw["fixed_branches"]).items()},
        attack_path=AttackPath(label=str(path["label"]), probe=str(path["probe"])),
        mitigation=dict(mitigation),
        distros=distros,
        kev=bool(raw.get("kev", False)),
        exploited_in_wild=bool(raw.get("exploited_in_wild", False)),
    )


def from_dict(doc, path="<dict>"):
    if not isinstance(doc, dict):
        raise TableError("%s: table root is not an object" % path)
    if "schema_version" not in doc:
        raise TableError("%s: missing schema_version" % path)
    if int(doc["schema_version"]) != SCHEMA_VERSION:
        raise TableError("%s: schema_version %r is not the supported %d"
                         % (path, doc["schema_version"], SCHEMA_VERSION))
    raw_cves = doc.get("cves")
    if not isinstance(raw_cves, list) or not raw_cves:
        raise TableError("%s: 'cves' must be a non-empty list" % path)
    cves = tuple(_parse_cve(raw) for raw in raw_cves)
    keys = [c.cve for c in cves]
    if len(set(keys)) != len(keys):
        raise TableError("%s: duplicate CVE ids in table" % path)
    return Table(
        path=path,
        schema_version=SCHEMA_VERSION,
        generated_at=str(doc.get("generated_at", "")),
        stale_after_days=int(doc.get("stale_after_days", 7)),
        cves=cves,
    )


def load(path):
    """Read + validate. Every failure names the path, because a dead path must be loud."""
    resolved = os.path.abspath(os.path.expanduser(path))
    if not os.path.isfile(resolved):
        raise TableError("fix table not found: %s" % resolved)
    try:
        with open(resolved, "r") as handle:
            doc = json.load(handle)
    except (OSError, IOError) as exc:
        raise TableError("cannot read fix table %s: %s" % (resolved, exc))
    except ValueError as exc:
        raise TableError("fix table %s is not valid JSON: %s" % (resolved, exc))
    return from_dict(doc, path=resolved)


def parse_timestamp(text):
    try:
        return datetime.strptime(text, _TS_FORMAT).replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def age_days(retrieved_at, now=None):
    """Whole days between a row's retrieval and ``now``. None when unparseable."""
    then = parse_timestamp(retrieved_at)
    if then is None:
        return None
    if now is None:
        current = datetime.now(timezone.utc)
    elif isinstance(now, str):
        current = parse_timestamp(now)
    else:
        current = now
    if current is None:
        return None
    return max(0, (current - then).days)


def is_stale(age, stale_after_days):
    """Unknown age counts as stale: fail toward 'look at this', never toward 'fine'."""
    if age is None:
        return True
    return age > max(0, int(stale_after_days))


DEFAULT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data", "fixed_versions.json")
