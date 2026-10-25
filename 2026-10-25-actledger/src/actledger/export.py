"""Self-contained audit bundles.

A bundle is the artifact you hand to someone outside the machine. It carries every
record, the head hash they must end at, and nothing that points back at the runtime —
no file paths, no database handles, no dependency on the ledger that produced it.
Verification needs this tool's stdlib code and the bundle. That is the whole trust base.
"""

import json
import os
from datetime import datetime, timezone
from typing import Optional, Sequence

from .chain import canonical_json, sha256_hex, verify_entries
from .models import Break, Entry, VerificationResult

BUNDLE_FORMAT = "actledger-bundle/1"

FORMAT_MISMATCH = "FORMAT-MISMATCH"
COUNT_MISMATCH = "COUNT-MISMATCH"
PARSE_ERROR = "PARSE-ERROR"


class ExportError(Exception):
    """Raised when a bundle cannot be written or read."""


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_bundle(entries: Sequence[Entry], generated_at: Optional[str] = None) -> dict:
    entries = list(entries)
    return {
        "format": BUNDLE_FORMAT,
        "generated_at": generated_at or _now(),
        "count": len(entries),
        "head_hash": entries[-1].hash if entries else "0" * 64,
        "entries": [entry.to_dict() for entry in entries],
    }


def bundle_digest(bundle: dict) -> str:
    """Digest of the evidence only — `generated_at` is metadata, not evidence."""
    return sha256_hex(
        canonical_json(
            {
                "count": bundle.get("count"),
                "head_hash": bundle.get("head_hash"),
                "entries": bundle.get("entries", []),
            }
        )
    )


def write_bundle(path: str, bundle: dict) -> None:
    directory = os.path.dirname(os.path.abspath(path))
    if not os.path.isdir(directory):
        raise ExportError("bundle directory does not exist: %s" % directory)
    try:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(bundle, handle, indent=2, sort_keys=True)
            handle.write("\n")
    except OSError as exc:
        raise ExportError("cannot write bundle %s: %s" % (path, exc))


def read_bundle(path: str) -> dict:
    if not os.path.exists(path):
        raise ExportError("no such bundle: %s" % path)
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError) as exc:
        raise ExportError("cannot read bundle %s: %s" % (path, exc))


def verify_bundle(bundle: dict) -> VerificationResult:
    breaks = []
    if bundle.get("format") != BUNDLE_FORMAT:
        breaks.append(
            Break(
                FORMAT_MISMATCH,
                0,
                "bundle format %r is not %r" % (bundle.get("format"), BUNDLE_FORMAT),
            )
        )

    entries = []
    for position, payload in enumerate(bundle.get("entries") or ()):
        try:
            entries.append(Entry.from_dict(payload))
        except (KeyError, TypeError, ValueError) as exc:
            breaks.append(Break(PARSE_ERROR, position, "entry %d is malformed: %s" % (position, exc)))

    declared = bundle.get("count")
    if declared != len(entries):
        breaks.append(
            Break(
                COUNT_MISMATCH,
                0,
                "bundle declares %s record(s) but carries %d (a record was dropped)"
                % (declared, len(entries)),
            )
        )

    result = verify_entries(entries, expected_head=bundle.get("head_hash"))
    return VerificationResult(
        ok=not breaks and result.ok,
        checked=result.checked,
        breaks=tuple(breaks) + result.breaks,
        head_hash=result.head_hash,
    )
