"""Immutable records for the skill ledger.

Everything here is a frozen dataclass; nothing in this package mutates a record after
construction. Ordering is a property of the collections, never of the filesystem walk.
"""

from dataclasses import dataclass, field
from typing import Tuple

# Ordered so reports are stable; the vocabulary is deliberately small and closed.
CAPABILITIES = (
    "network",
    "exec",
    "code_eval",
    "fs_write",
    "credentials",
    "hermes_surface",
)

CAPABILITY_HELP = {
    "network": "reaches the network",
    "exec": "runs a subprocess or shell",
    "code_eval": "evaluates generated code",
    "fs_write": "writes or deletes files",
    "credentials": "reads credentials or environment secrets",
    "hermes_surface": "reads this host's agent state (~/.hermes, state.db, memory)",
}


@dataclass(frozen=True)
class ScriptRef:
    """One script file shipped inside a skill directory."""

    rel: str
    path: str
    sha256: str
    size: int
    capabilities: frozenset = field(default_factory=frozenset)
    signals: Tuple[str, ...] = ()
    truncated: bool = False

    def to_dict(self):
        return {
            "rel": self.rel,
            "path": self.path,
            "sha256": self.sha256,
            "size": self.size,
            "capabilities": sorted(self.capabilities),
            "signals": list(self.signals),
            "truncated": self.truncated,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            rel=data["rel"],
            path=data["path"],
            sha256=data["sha256"],
            size=int(data["size"]),
            capabilities=frozenset(data.get("capabilities", ())),
            signals=tuple(data.get("signals", ())),
            truncated=bool(data.get("truncated", False)),
        )


@dataclass(frozen=True)
class SkillRecord:
    """One installed skill, as found on disk."""

    root: str
    name: str
    rel: str
    path: str
    skill_md_sha256: str
    mtime_ns: int
    declared_tools: Tuple[str, ...] = ()
    frontmatter_ok: bool = True
    problem: str = ""
    scripts: Tuple[ScriptRef, ...] = ()

    @property
    def key(self):
        return "%s:%s" % (self.root, self.rel)

    @property
    def capabilities(self):
        caps = set()
        for script in self.scripts:
            caps.update(script.capabilities)
        return frozenset(caps)

    @property
    def signature(self):
        """Identity of the installed content: SKILL.md plus every script hash."""
        parts = [self.skill_md_sha256]
        parts.extend("%s=%s" % (s.rel, s.sha256) for s in self.scripts)
        parts.extend(self.declared_tools)
        return "|".join(parts)

    def to_dict(self):
        return {
            "root": self.root,
            "name": self.name,
            "rel": self.rel,
            "path": self.path,
            "skill_md_sha256": self.skill_md_sha256,
            "mtime_ns": self.mtime_ns,
            "declared_tools": list(self.declared_tools),
            "frontmatter_ok": self.frontmatter_ok,
            "problem": self.problem,
            "capabilities": sorted(self.capabilities),
            "scripts": [s.to_dict() for s in self.scripts],
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            root=data["root"],
            name=data["name"],
            rel=data["rel"],
            path=data["path"],
            skill_md_sha256=data["skill_md_sha256"],
            mtime_ns=int(data["mtime_ns"]),
            declared_tools=tuple(data.get("declared_tools", ())),
            frontmatter_ok=bool(data.get("frontmatter_ok", True)),
            problem=data.get("problem", ""),
            scripts=tuple(ScriptRef.from_dict(s) for s in data.get("scripts", ())),
        )


@dataclass(frozen=True)
class Root:
    label: str
    path: str
    kind: str = "profile"  # "profile" | "shared"


@dataclass(frozen=True)
class Ledger:
    """The whole measured surface at one moment."""

    roots: Tuple[Root, ...]
    skills: Tuple[SkillRecord, ...]
    generated_at: str = ""
    unreadable: Tuple[str, ...] = ()
    excluded: Tuple[str, ...] = ()

    def scripts(self):
        for skill in self.skills:
            for script in skill.scripts:
                yield skill, script

    def to_dict(self):
        return {
            "tool": "skillbom",
            "version": 1,
            "generated_at": self.generated_at,
            "roots": [{"label": r.label, "path": r.path, "kind": r.kind} for r in self.roots],
            "unreadable": list(self.unreadable),
            "excluded": list(self.excluded),
            "skills": [s.to_dict() for s in self.skills],
        }

    @classmethod
    def from_dict(cls, data):
        roots = tuple(
            Root(label=r["label"], path=r["path"], kind=r.get("kind", "profile"))
            for r in data.get("roots", ())
        )
        return cls(
            roots=roots,
            skills=tuple(SkillRecord.from_dict(s) for s in data.get("skills", ())),
            generated_at=data.get("generated_at", ""),
            unreadable=tuple(data.get("unreadable", ())),
            excluded=tuple(data.get("excluded", ())),
        )
