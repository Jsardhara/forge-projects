"""pubgate engine — the single assertion this tool makes:

    published artifact == build(upstream source)

Two independent checks, both offline and stdlib-only:

1. ``verify_record``  — internal consistency. Every member of a wheel must match the
   sha256 the build recorded for it, and nothing may ride along unlisted.
2. ``verify_source``  — external correspondence. Every source file you audited must
   appear in the artifact with byte-identical content.

(1) alone is not enough: an attacker who controls the build can rewrite RECORD. (2) is
the hop that fails in the LiteLLM 1.107.0 shape — clean source, poisoned wheels.
"""

from __future__ import annotations

import base64
import csv
import hashlib
import io
import json
import os
import zipfile
from typing import Dict, List, NamedTuple, Optional

MANIFEST_SCHEMA = "pubgate.manifest.v1"

_SKIP_DIRS = frozenset(
    {
        ".git", ".hg", ".svn", "__pycache__", ".mypy_cache", ".pytest_cache",
        ".ruff_cache", "node_modules", ".venv", "venv", "build", "dist",
        ".tox", ".eggs",
    }
)
_SKIP_SUFFIXES = (".pyc", ".pyo", ".egg-info")
_DIST_INFO = ".dist-info/"


class Violation(NamedTuple):
    kind: str
    path: str
    detail: str

    def __str__(self) -> str:
        return "{} {} — {}".format(self.kind, self.path, self.detail)


class PubgateError(Exception):
    """Raised for unusable inputs (missing file, not a zip). Never swallowed."""


# --------------------------------------------------------------------------- hashing
def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def iau_digest(files: Dict[str, str]) -> str:
    """Order-independent digest over a {relpath: sha256} map."""
    canon = "".join("{}  {}\n".format(files[k], k) for k in sorted(files))
    return sha256_bytes(canon.encode("utf-8"))


def record_digest(data: bytes) -> str:
    """Encode a digest exactly as PEP 427 RECORD does: urlsafe base64, unpadded."""
    return base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode("ascii")


_HEX = frozenset("0123456789abcdef")


def _normalize_digest(value: str) -> Optional[str]:
    """Return the digest as lowercase hex, whatever spelling RECORD used.

    Real wheels carry urlsafe-base64; hand-built or third-party tooling may emit hex.
    Both mean the same bytes, so both normalise to one comparable form.
    """
    v = value.strip()
    if len(v) == 64 and set(v.lower()) <= _HEX:
        return v.lower()
    try:
        raw = base64.urlsafe_b64decode(v + "=" * (-len(v) % 4))
    except (ValueError, TypeError):
        return None
    return raw.hex() if len(raw) == 32 else None


# ------------------------------------------------------------------ wheel internals
def _record_member(names: List[str]) -> Optional[str]:
    for n in names:
        if n.endswith(_DIST_INFO + "RECORD") or n == "RECORD":
            return n
    return None


def record_hashes(wheel_path: str) -> Dict[str, str]:
    """Parse ``<dist-info>/RECORD`` into {member: sha256}.

    RECORD rows carry an empty hash for RECORD itself, so those are skipped.
    """
    _require_file(wheel_path)
    try:
        with zipfile.ZipFile(wheel_path) as zf:
            target = _record_member(zf.namelist())
            if target is None:
                raise PubgateError("no RECORD member in {}".format(wheel_path))
            raw = zf.read(target).decode("utf-8", "replace")
    except zipfile.BadZipFile as exc:
        raise PubgateError("not a wheel (bad zip): {} ({})".format(wheel_path, exc))

    out: Dict[str, str] = {}
    for row in csv.reader(io.StringIO(raw)):
        if not row or len(row) < 2:
            continue
        path, digest = row[0].strip(), row[1].strip()
        if not path or "=" not in digest:
            continue
        algo, _, value = digest.partition("=")
        if algo.strip().lower() != "sha256":
            continue
        norm = _normalize_digest(value)
        if norm:
            out[path] = norm
    return out


def wheel_version(wheel_path: str) -> Optional[str]:
    """Version from the artifact's own METADATA, unverified (context only)."""
    _require_file(wheel_path)
    with zipfile.ZipFile(wheel_path) as zf:
        for n in zf.namelist():
            if n.endswith(_DIST_INFO + "METADATA"):
                for line in zf.read(n).decode("utf-8", "replace").splitlines():
                    if line.lower().startswith("version:"):
                        return line.split(":", 1)[1].strip()
    return None


def _members(wheel_path: str) -> Dict[str, bytes]:
    with zipfile.ZipFile(wheel_path) as zf:
        return {n: zf.read(n) for n in zf.namelist() if not n.endswith("/")}


def _is_metadata(member: str) -> bool:
    return _DIST_INFO in member or member.endswith("/RECORD")


# ------------------------------------------------------ check 1: RECORD consistency
def verify_record(wheel_path: str) -> List[Violation]:
    """Every artifact member must equal its recorded digest; nothing unlisted."""
    recorded = record_hashes(wheel_path)
    present = _members(wheel_path)
    out: List[Violation] = []

    for member in sorted(present):
        if _is_metadata(member):
            continue
        if member not in recorded:
            out.append(Violation("RECORD_UNLISTED", member,
                                 "present in artifact but absent from RECORD"))
            continue
        actual = sha256_bytes(present[member])
        if actual != recorded[member]:
            out.append(Violation(
                "RECORD_MISMATCH", member,
                "RECORD says {}…, artifact is {}…".format(
                    recorded[member][:12], actual[:12]),
            ))

    for member in sorted(recorded):
        if member not in present:
            out.append(Violation("RECORD_MISSING", member,
                                 "listed in RECORD but absent from artifact"))
    return out


# ------------------------------------------------------------- source attestation
def source_manifest(root: str, name: Optional[str] = None,
                    version: Optional[str] = None) -> dict:
    """Hash an audited source tree into a portable manifest."""
    if not os.path.isdir(root):
        raise PubgateError("source directory not found: {}".format(root))

    files: Dict[str, str] = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in _SKIP_DIRS)
        for fname in sorted(filenames):
            if fname.endswith(_SKIP_SUFFIXES):
                continue
            full = os.path.join(dirpath, fname)
            if not os.path.isfile(full):
                continue
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            files[rel] = sha256_file(full)

    return {
        "schema": MANIFEST_SCHEMA,
        "name": name,
        "version": version,
        "digest": iau_digest(files),
        "file_count": len(files),
        "files": files,
    }


def load_manifest(path: str) -> dict:
    _require_file(path)
    with open(path, "r", encoding="utf-8") as fh:
        try:
            man = json.load(fh)
        except json.JSONDecodeError as exc:
            raise PubgateError("manifest is not valid JSON: {} ({})".format(path, exc))
    if man.get("schema") != MANIFEST_SCHEMA:
        raise PubgateError(
            "unexpected manifest schema {!r}, want {!r}".format(
                man.get("schema"), MANIFEST_SCHEMA))
    if not isinstance(man.get("files"), dict):
        raise PubgateError("manifest has no 'files' map: {}".format(path))
    return man


# ------------------------------------------------- check 2: source correspondence
def _package_roots(members: List[str]) -> set:
    """Top-level importable entries inside the artifact — packages *and* modules.

    A single-module distribution (``six.py``) has no directory, so file members count.
    """
    roots = set()
    for m in members:
        if _is_metadata(m):
            continue
        roots.add(m.split("/", 1)[0])
    return roots


def _wheel_member_for(rel_source_path: str) -> str:
    """Map an audited source path onto its expected artifact path.

    ``src/demo/core.py`` -> ``demo/core.py`` (src layout);
    ``demo/core.py``      -> ``demo/core.py`` (flat layout).
    """
    parts = rel_source_path.split("/")
    if parts and parts[0] == "src" and len(parts) > 1:
        return "/".join(parts[1:])
    return rel_source_path


def verify_source(wheel_path: str, manifest: dict) -> List[Violation]:
    """Every audited source file must appear byte-identical in the artifact."""
    present = _members(wheel_path)
    artifact_hashes = {
        m: sha256_bytes(b) for m, b in present.items() if not _is_metadata(m)
    }
    roots = _package_roots(list(present))
    out: List[Violation] = []

    man_version = manifest.get("version")
    art_version = wheel_version(wheel_path)
    if man_version and art_version and man_version != art_version:
        out.append(Violation("VERSION_MISMATCH", "METADATA",
                             "manifest {}, artifact {}".format(man_version, art_version)))
    if manifest.get("name") and art_version and not man_version:
        out.append(Violation("VERSION_UNPINNED", "METADATA",
                             "manifest records no version; cannot bind to artifact"))

    for rel in sorted(manifest["files"]):
        member = _wheel_member_for(rel)
        head = member.split("/", 1)[0]
        if head not in roots:
            continue  # tests/docs/pyproject: audited, but not shipped by design
        if member not in artifact_hashes:
            out.append(Violation("SOURCE_ABSENT", rel,
                                 "audited source file missing from artifact as {}".format(member)))
            continue
        if artifact_hashes[member] != manifest["files"][rel]:
            out.append(Violation(
                "SOURCE_MISMATCH", rel,
                "artifact content {}… != audited source {}".format(
                    artifact_hashes[member][:12], manifest["files"][rel][:12]),
            ))
    return out


# ------------------------------------------------------------------------ helpers
def exit_code(violations: List[Violation]) -> int:
    return 0 if not violations else 1


def _require_file(path: str) -> None:
    if not os.path.isfile(path):
        raise PubgateError("file not found: {}".format(path))
