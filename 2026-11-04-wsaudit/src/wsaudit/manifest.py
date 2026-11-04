"""Manifest build / save / load / compare.

A manifest is the recorded expectation: one model digest plus the per-tensor
digest behind it. Comparison is fail-closed - anything it cannot check is a
problem, not a pass.
"""

import json
import os
from dataclasses import dataclass, field

from .errors import WsAuditError

TOOL = "wsaudit"
REQUIRED = ("tool", "format", "model_digest", "tensors")


@dataclass(frozen=True)
class Comparison:
    ok: bool
    checked: int = 0
    problems: tuple = field(default_factory=tuple)


def build_manifest(model):
    return {
        "tool": TOOL,
        "version": 1,
        "format": model.format,
        "model_digest": model.model_digest,
        "partial": model.partial,
        "tensor_count": model.tensor_count,
        "total_bytes": model.total_bytes,
        "tensors": {
            item.name: {
                "dtype": item.dtype,
                "shape": list(item.shape),
                "sha256": item.sha256,
            }
            for item in model.tensors
        },
    }


def save_manifest(payload, path):
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, sort_keys=True)
            fh.write("\n")
    except OSError as exc:
        raise WsAuditError("cannot write manifest %s (%s)" % (path, exc))


def load_manifest(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
    except OSError as exc:
        raise WsAuditError("cannot read manifest %s (%s)" % (path, exc))
    except ValueError as exc:
        raise WsAuditError("manifest %s is not valid JSON (%s)" % (path, exc))
    if not isinstance(payload, dict):
        raise WsAuditError("manifest %s is not a JSON object" % path)
    missing = [key for key in REQUIRED if key not in payload]
    if missing:
        raise WsAuditError(
            "manifest %s is missing required key(s): %s" % (path, ", ".join(missing))
        )
    if not isinstance(payload["tensors"], dict):
        raise WsAuditError("manifest %s: 'tensors' is not an object" % path)
    return payload


def compare(model, payload):
    if model.partial:
        return Comparison(
            ok=False,
            checked=0,
            problems=("model was scanned partial (header-only); a partial digest cannot be verified",),
        )

    problems = []
    recorded = payload.get("tensors", {})
    seen = 0
    for item in model.tensors:
        expected = recorded.get(item.name)
        if expected is None:
            problems.append("tensor %r is missing from the manifest" % item.name)
            continue
        seen += 1
        if expected.get("sha256") != item.sha256:
            problems.append("tensor %r sha256 differs from the manifest" % item.name)
        if tuple(expected.get("shape") or ()) != tuple(item.shape):
            problems.append("tensor %r shape differs from the manifest" % item.name)
        if expected.get("dtype") != item.dtype:
            problems.append("tensor %r dtype differs from the manifest" % item.name)

    for name in recorded:
        if not any(item.name == name for item in model.tensors):
            problems.append("tensor %r is recorded but not present in the model" % name)

    if payload.get("model_digest") != model.model_digest:
        problems.append(
            "model digest differs from the manifest (%s != %s)"
            % (model.model_digest[:16], str(payload.get("model_digest"))[:16])
        )

    return Comparison(ok=not problems, checked=seen, problems=tuple(problems))


def load_and_compare(model, path):
    return compare(model, load_manifest(path))


def exists(path):
    return os.path.isfile(path)
