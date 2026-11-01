"""Walk skill roots and build a ledger. Read-only: nothing here writes or executes.

Filesystem rules that matter:
  * a skill is any directory holding a `SKILL.md`, wherever it sits under the root;
  * a script belongs to its nearest enclosing skill directory;
  * directories whose own name starts with `_` or `.` (`_trash`, `.archive`) are skipped
    *and counted*, so a pruned tree is visible instead of looking empty;
  * a root that cannot be walked, or that yields zero skills, is UNMEASURABLE - never
    an empty ledger, because "no skills" and "I could not look" must not read the same.
"""

import hashlib
import os
from datetime import datetime, timezone

from .classify import classify_text
from .frontmatter import parse_frontmatter
from .models import Ledger, Root, ScriptRef, SkillRecord

SCRIPT_SUFFIXES = (".sh", ".bash", ".py", ".js", ".mjs", ".cjs", ".ts", ".rb", ".pl", ".zsh")
SKILL_FILE = "SKILL.md"
MAX_CLASSIFY_BYTES = 512 * 1024
SKIPPED_PREFIXES = ("_", ".")


def _utc_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _is_script(name):
    return name.lower().endswith(SCRIPT_SUFFIXES)


def _walk(root_path, excluded):
    """Yield (dirpath, filenames) for the tree, pruning skip-dirs and recording them."""
    for dirpath, dirnames, filenames in os.walk(root_path, topdown=True, onerror=None):
        kept = []
        for name in sorted(dirnames):
            full = os.path.join(dirpath, name)
            if name.startswith(SKIPPED_PREFIXES):
                excluded.append(full)
            else:
                kept.append(name)
        dirnames[:] = kept
        yield dirpath, sorted(filenames)


def _read_text(path, unreadable):
    try:
        with open(path, "rb") as fh:
            data = fh.read()
    except OSError as exc:
        unreadable.append("%s: %s" % (path, exc.__class__.__name__))
        return None
    return data


def _script_ref(path, skill_dir, unreadable):
    data = _read_text(path, unreadable)
    if data is None:
        return None
    window = data[:MAX_CLASSIFY_BYTES]
    result = classify_text(window.decode("utf-8", errors="replace"))
    return ScriptRef(
        rel=os.path.relpath(path, skill_dir),
        path=path,
        sha256=hashlib.sha256(data).hexdigest(),
        size=len(data),
        capabilities=result.capabilities,
        signals=result.signals,
        truncated=len(data) > len(window),
    )


def _skill_record(skill_path, skill_dir, root, unreadable):
    rel = os.path.relpath(skill_dir, root.path)
    data = _read_text(skill_path, unreadable)
    if data is None:
        return None
    front = parse_frontmatter(data.decode("utf-8", errors="replace"))
    name = front.name or os.path.basename(skill_dir.rstrip(os.sep))
    try:
        mtime_ns = os.stat(skill_path).st_mtime_ns
    except OSError:
        mtime_ns = 0
    return SkillRecord(
        root=root.label,
        name=name,
        rel="" if rel == "." else rel,
        path=skill_dir,
        skill_md_sha256=hashlib.sha256(data).hexdigest(),
        mtime_ns=mtime_ns,
        declared_tools=front.tools,
        frontmatter_ok=front.ok,
        problem=front.problem,
        scripts=(),
    )


def _nearest_skill_dir(path, skill_dirs):
    current = os.path.dirname(path)
    while True:
        if current in skill_dirs:
            return current
        parent = os.path.dirname(current)
        if parent == current:
            return None
        current = parent


def _scan_root(root, unreadable, excluded):
    if not os.path.exists(root.path):
        unreadable.append("root '%s': no such directory: %s" % (root.label, root.path))
        return ()
    if not os.path.isdir(root.path):
        unreadable.append("root '%s': not a directory: %s" % (root.label, root.path))
        return ()

    walked = list(_walk(root.path, excluded))
    skill_paths = [
        os.path.join(dirpath, name)
        for dirpath, filenames in walked
        for name in filenames
        if name == SKILL_FILE
    ]
    if not skill_paths:
        unreadable.append("root '%s': no %s found under %s" % (root.label, SKILL_FILE, root.path))
        return ()

    records = {}
    for skill_path in sorted(skill_paths):
        skill_dir = os.path.dirname(skill_path)
        record = _skill_record(skill_path, skill_dir, root, unreadable)
        if record is not None:
            records[skill_dir] = record

    skill_dirs = set(records)
    scripts = {d: [] for d in skill_dirs}
    for dirpath, filenames in walked:
        for name in filenames:
            if name == SKILL_FILE or not _is_script(name):
                continue
            path = os.path.join(dirpath, name)
            owner = _nearest_skill_dir(path, skill_dirs)
            if owner is None:
                excluded.append("orphan-script:" + path)
                continue
            ref = _script_ref(path, owner, unreadable)
            if ref is not None:
                scripts[owner].append(ref)

    out = []
    for skill_dir, record in records.items():
        out.append(
            SkillRecord(
                root=record.root,
                name=record.name,
                rel=record.rel,
                path=record.path,
                skill_md_sha256=record.skill_md_sha256,
                mtime_ns=record.mtime_ns,
                declared_tools=record.declared_tools,
                frontmatter_ok=record.frontmatter_ok,
                problem=record.problem,
                scripts=tuple(sorted(scripts[skill_dir], key=lambda s: s.rel)),
            )
        )
    return tuple(sorted(out, key=lambda r: (r.rel, r.name)))


def scan_roots(roots, now=None):
    """Build a Ledger from an immutable sequence of Root descriptors."""
    unreadable = []
    excluded = []
    skills = []
    for root in roots:
        skills.extend(_scan_root(root, unreadable, excluded))
    return Ledger(
        roots=tuple(roots),
        skills=tuple(sorted(skills, key=lambda r: (r.root, r.rel, r.name))),
        generated_at=now or _utc_now(),
        unreadable=tuple(unreadable),
        excluded=tuple(excluded),
    )


def default_roots(home=None, include_global=False):
    """The roots audited when no --root is given: every profile's skills store."""
    home = home or os.path.expanduser("~")
    profiles_dir = os.path.join(home, ".hermes", "profiles")
    roots = []
    if os.path.isdir(profiles_dir):
        for label in sorted(os.listdir(profiles_dir)):
            path = os.path.join(profiles_dir, label, "skills")
            if os.path.isdir(path):
                roots.append(_root(label, path, "profile"))
    if include_global:
        shared = os.path.join(home, ".hermes", "skills")
        if os.path.isdir(shared):
            roots.append(_root("shared", shared, "shared"))
    return tuple(roots)


def _root(label, path, kind):
    return Root(label=label, path=path, kind=kind)
