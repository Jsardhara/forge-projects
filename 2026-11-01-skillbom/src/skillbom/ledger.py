"""Ledger serialisation, drift and fleet-level aggregation.

Two different questions live here and they are easy to confuse:

  * **drift** - did this host's installed skills change since the last ledger?
  * **divergence** - do two copies of the same skill, *right now*, disagree with
    each other? A fleet of nine profiles can be internally inconsistent while being
    perfectly stable over time, and stable over time while internally inconsistent.
"""

from dataclasses import dataclass
from typing import Tuple

from .models import CAPABILITIES, Ledger


@dataclass(frozen=True)
class Drift:
    added: Tuple[str, ...] = ()
    removed: Tuple[str, ...] = ()
    changed: Tuple[str, ...] = ()

    def __bool__(self):
        return bool(self.added or self.removed or self.changed)

    @property
    def total(self):
        return len(self.added) + len(self.removed) + len(self.changed)

    def to_dict(self):
        return {
            "added": list(self.added),
            "removed": list(self.removed),
            "changed": list(self.changed),
        }


@dataclass(frozen=True)
class Copy:
    root: str
    rel: str
    sha256: str

    def to_dict(self):
        return {"root": self.root, "rel": self.rel, "sha256": self.sha256}


@dataclass(frozen=True)
class Divergence:
    name: str
    copies: Tuple[Copy, ...]

    @property
    def hashes(self):
        return sorted({c.sha256 for c in self.copies})


def ledger_to_json(ledger):
    return ledger.to_dict()


def ledger_from_json(data):
    if not isinstance(data, dict) or "skills" not in data:
        raise ValueError("not a skillbom ledger")
    return Ledger.from_dict(data)


def _by_key(ledger):
    return {skill.key: skill for skill in ledger.skills}


def diff_ledgers(previous, current):
    """Compare two ledgers by content signature, not by mtime."""
    before = _by_key(previous)
    after = _by_key(current)
    added = tuple(sorted(set(after) - set(before)))
    removed = tuple(sorted(set(before) - set(after)))
    changed = tuple(
        sorted(
            key
            for key in set(before) & set(after)
            if before[key].signature != after[key].signature
        )
    )
    return Drift(added=added, removed=removed, changed=changed)


def group_copies(ledger):
    """Skill name -> every installed copy of it, across all audited roots."""
    groups = {}
    for skill in ledger.skills:
        groups.setdefault(skill.name, []).append(skill)
    return {name: tuple(sorted(items, key=lambda s: (s.root, s.rel))) for name, items in groups.items()}


def divergence(ledger):
    """Copies that share a name but not a content hash."""
    found = []
    for name, copies in sorted(group_copies(ledger).items()):
        refs = tuple(Copy(root=s.root, rel=s.rel, sha256=s.skill_md_sha256) for s in copies)
        if len(refs) > 1 and len({r.sha256 for r in refs}) > 1:
            found.append(Divergence(name=name, copies=refs))
    return tuple(found)


def skill_counts(ledger):
    """(installed copies, distinct skill names)."""
    return len(ledger.skills), len({s.name for s in ledger.skills})


def capability_counts(ledger):
    """Number of *scripts* carrying each capability."""
    counts = {cap: 0 for cap in CAPABILITIES}
    for _skill, script in ledger.scripts():
        for cap in script.capabilities:
            counts[cap] = counts.get(cap, 0) + 1
    return counts


def skill_capability_counts(ledger):
    """Number of *skills* carrying each capability."""
    counts = {cap: 0 for cap in CAPABILITIES}
    for skill in ledger.skills:
        for cap in skill.capabilities:
            counts[cap] = counts.get(cap, 0) + 1
    return counts


def script_count(ledger):
    return sum(len(s.scripts) for s in ledger.skills)


def root_counts(ledger):
    """Per-root skill and script counts, in root order."""
    rows = []
    for root in ledger.roots:
        skills = [s for s in ledger.skills if s.root == root.label]
        rows.append((root.label, len(skills), sum(len(s.scripts) for s in skills)))
    return tuple(rows)


def top_skills(ledger, limit=10):
    """Highest-authority skills: most distinct capabilities, then most scripts."""
    ranked = sorted(
        ledger.skills,
        key=lambda s: (-len(s.capabilities), -len(s.scripts), s.root, s.rel),
    )
    return tuple(ranked[:limit]) if limit else ()


def frontmatter_problems(ledger):
    return tuple(s for s in ledger.skills if not s.frontmatter_ok)
