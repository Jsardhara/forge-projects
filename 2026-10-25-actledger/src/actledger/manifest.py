"""Bind a *measured* model digest to a ledger row.

`ActionRecord.model_digest` is a string a caller types. `audit` can only ask whether it
is non-empty, which makes the ledger's model-identity axis unfalsifiable: `abcdef` passes
exactly as well as a real digest of the wrong model.

`wsaudit` (2026-11-04) already measures weights - per-tensor sha256 over the real byte
range plus one canonical model digest. This module is the other half of that binding:

* it re-derives the canonical digest from a wsaudit manifest's own tensor list, so the
  value written into the ledger is *computed here*, not transcribed;
* it refuses a manifest that disagrees with itself, is header-only, or declares no
  tensors - a partial or inconsistent measurement must never reach a record;
* it writes one binding line beside the ledger, which is what `audit` reads. A digest
  that merely *looks* measured (starts with `ws1:`) but has no binding line is reported
  as UNMEASURED, because a string is not evidence.

The canonical digest algorithm is wsaudit's, reimplemented here rather than imported:
these projects do not share a package, and the format is twelve lines. It is pinned by
a fixture produced by wsaudit itself (`tests/data/minilm.manifest.json`), so the two
implementations are checked against each other on every test run.
"""

import hashlib
import json
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional

TOOL = "wsaudit"
DIGEST_TAG = "ws1:"
FORMATS = ("gguf", "safetensors")
REQUIRED = ("tool", "format", "model_digest", "partial", "tensors")

_HEX64 = re.compile(r"^[0-9a-f]{64}$")


class ManifestError(Exception):
    """The manifest cannot be trusted as a measurement."""


class BindingError(Exception):
    """The binding file beside a ledger is unreadable or self-contradictory."""


@dataclass(frozen=True)
class DerivedDigest:
    """A digest recomputed from a manifest's tensor list, plus what it covers."""

    digest: str
    tagged: str
    tensor_count: int
    format: str
    manifest_sha256: str


def _canonical_bytes(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def manifest_sha256(payload: Mapping[str, Any]) -> str:
    """Fingerprint of the manifest this digest came from, so the file can be found."""
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def canonical_digest(tensors: Mapping[str, Any], partial: bool = False) -> str:
    """One digest over sorted (name, dtype, shape, hash) tuples.

    Every field is length-prefixed so that ('a|b', 'cc') cannot collide with
    ('a', 'bb|cc') - the field boundary is encoded, never inferred from the separator.
    """
    hasher = hashlib.sha256()
    hasher.update(b"wsaudit/v1\n")
    hasher.update(b"partial\n" if partial else b"full\n")
    for name in sorted(tensors):
        entry = tensors[name]
        shape = ",".join(str(dim) for dim in entry.get("shape") or ())
        digest = entry.get("sha256") or ""
        dtype = entry.get("dtype") or ""
        line = "%d:%s%d:%s%d:%s%d:%s\n" % (
            len(name), name,
            len(dtype), dtype,
            len(shape), shape,
            len(digest), digest,
        )
        hasher.update(line.encode("utf-8"))
    return hasher.hexdigest()


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _check_tensor(name: str, entry: Any, partial: bool) -> None:
    if not isinstance(entry, dict):
        raise ManifestError("tensor %r is not an object" % name)
    if not isinstance(entry.get("dtype"), str) or not entry["dtype"]:
        raise ManifestError("tensor %r has no dtype" % name)
    shape = entry.get("shape")
    if not isinstance(shape, list) or not all(_is_int(dim) for dim in shape):
        raise ManifestError("tensor %r shape is not a list of integers" % name)
    if partial:
        return
    sha = entry.get("sha256")
    if not isinstance(sha, str) or not _HEX64.match(sha.lower()):
        raise ManifestError(
            "tensor %r sha256 is not 64 hex characters (%r)" % (name, sha)
        )


def load_manifest(path: str) -> Dict[str, Any]:
    """Read and shape-check a wsaudit manifest. Values are not re-derived here."""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except OSError as exc:
        raise ManifestError("cannot read manifest %s (%s)" % (path, exc))
    except ValueError as exc:
        raise ManifestError("manifest %s is not valid JSON (%s)" % (path, exc))

    if not isinstance(payload, dict):
        raise ManifestError("manifest %s is not a JSON object" % path)

    missing = [key for key in REQUIRED if key not in payload]
    if missing:
        raise ManifestError(
            "manifest %s is missing required key(s): %s" % (path, ", ".join(missing))
        )
    if payload["tool"] != TOOL:
        raise ManifestError(
            "manifest %s was produced by %r, not %r - this digest algorithm is %s-only"
            % (path, payload["tool"], TOOL, TOOL)
        )
    if payload["format"] not in FORMATS:
        raise ManifestError(
            "manifest %s declares unknown format %r (expected one of %s)"
            % (path, payload["format"], ", ".join(FORMATS))
        )
    recorded = payload["model_digest"]
    if not isinstance(recorded, str) or not _HEX64.match(recorded.lower()):
        raise ManifestError(
            "manifest %s model_digest is not 64 hex characters (%r)" % (path, recorded)
        )
    if not isinstance(payload["partial"], bool):
        raise ManifestError("manifest %s field 'partial' is not a boolean" % path)
    tensors = payload["tensors"]
    if not isinstance(tensors, dict):
        raise ManifestError("manifest %s: 'tensors' is not an object" % path)

    for name in tensors:
        _check_tensor(name, tensors[name], partial=payload["partial"])
    return payload


def derive(path: str) -> DerivedDigest:
    """Load a manifest, recompute its digest, and refuse anything that does not agree."""
    payload = load_manifest(path)
    if payload["partial"]:
        raise ManifestError(
            "manifest %s is partial (header-only); a partial digest cannot be bound to a "
            "record - re-run the scan without --header-only" % path
        )
    tensors = payload["tensors"]
    if not tensors:
        raise ManifestError("manifest %s declares no tensors" % path)

    recomputed = canonical_digest(tensors)
    recorded = payload["model_digest"].lower()
    if recomputed != recorded:
        raise ManifestError(
            "manifest %s is inconsistent: model_digest %s does not equal the digest "
            "recomputed from its %d tensor(s) (%s)"
            % (path, recorded[:16], len(tensors), recomputed[:16])
        )
    return DerivedDigest(
        digest=recomputed,
        tagged=DIGEST_TAG + recomputed,
        tensor_count=len(tensors),
        format=payload["format"],
        manifest_sha256=manifest_sha256(payload),
    )


def is_tagged(value: str) -> bool:
    return bool(isinstance(value, str) and value.startswith(DIGEST_TAG)
                and _HEX64.match(value[len(DIGEST_TAG):].lower()))


def bare_hex(value: str) -> Optional[str]:
    """The 64-hex digest inside a value, tagged or not. None when it is not a digest."""
    if not isinstance(value, str):
        return None
    text = value.strip().lower()
    if text.startswith(DIGEST_TAG):
        text = text[len(DIGEST_TAG):]
    return text if _HEX64.match(text) else None


# ------------------------------------------------------------------ binding sidecar
#
# `<ledger>.manifests.jsonl` - one line per bound record. It lives beside the ledger
# rather than inside it because a record's field set is hashed into the chain: adding a
# key would invalidate every ledger written before today. The chain still proves the
# digest was not edited after the fact; this file proves a tool derived it in the first
# place.


def binding_path(ledger_path: str) -> str:
    return ledger_path + ".manifests.jsonl"


def append_binding(ledger_path: str, seq: int, derived: DerivedDigest,
                   manifest_path: str, recorded_at: str) -> None:
    line = {
        "seq": int(seq),
        "model_digest": derived.tagged,
        "format": derived.format,
        "tensor_count": derived.tensor_count,
        "manifest_sha256": derived.manifest_sha256,
        "manifest": os.path.abspath(manifest_path),
        "recorded_at": recorded_at,
    }
    try:
        with open(binding_path(ledger_path), "a", encoding="utf-8") as handle:
            handle.write(json.dumps(line, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as exc:
        raise BindingError("cannot write binding for seq %d (%s)" % (seq, exc))


def load_bindings(ledger_path: str) -> Dict[int, str]:
    """seq -> the digest a tool derived for it. Absent file means nothing was bound."""
    path = binding_path(ledger_path)
    if not os.path.exists(path):
        return {}
    bindings: Dict[int, str] = {}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            lines = handle.read().splitlines()
    except OSError as exc:
        raise BindingError("cannot read binding file %s (%s)" % (path, exc))

    for number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except ValueError:
            raise BindingError(
                "binding file %s line %d is not valid JSON - cannot tell which rows were "
                "measured" % (path, number)
            )
        if not isinstance(payload, dict) or "seq" not in payload or "model_digest" not in payload:
            raise BindingError(
                "binding file %s line %d is not a binding record" % (path, number)
            )
        try:
            seq = int(payload["seq"])
        except (TypeError, ValueError):
            raise BindingError("binding file %s line %d has a non-integer seq" % (path, number))
        if seq in bindings:
            raise BindingError(
                "binding file %s binds seq %d twice - a ledger seq is written once" % (path, seq)
            )
        bindings[seq] = str(payload["model_digest"])
    return bindings
