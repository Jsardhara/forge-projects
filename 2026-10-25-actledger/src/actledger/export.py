"""Self-contained audit bundles.

A bundle is the artifact you hand to someone outside the machine. It carries every
record, the head hash they must end at, the derivation of every measured digest, and the
posture those records earned at export time — and nothing that points back at the
runtime: no file paths, no database handles, no dependency on the ledger that produced
it. Verification needs this tool's stdlib code and the bundle. That is the whole trust
base.

Until format 2 that sentence was true for immutability and false for the other two legs.
The bundle carried `ws1:` digests and `verifier` columns with none of the verdicts that
judge them, so a receiver could prove the records were not altered and could not prove a
single digest had been derived rather than typed. `bundleproof` closes that: `verify_bundle`
now recomputes both legs from the artifact's own contents, and a bundle that carries no
bindings reports `BINDINGS-ABSENT` — not checkable, which is not the same answer as clean.
"""

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Mapping, Optional, Sequence, Tuple, Union

from .bundleproof import (
    ABSENT,
    ABSENT as BINDINGS_ABSENT,
    MISMATCH,
    PASS,
    UNMEASURABLE,
    BindingCheck,
    Proof,
    prove,
)
from .audit import audit
from .chain import canonical_json, sha256_hex, verify_entries
from .manifest import Binding
from .models import Break, Entry, VerificationResult

BUNDLE_FORMAT_V1 = "actledger-bundle/1"
BUNDLE_FORMAT = "actledger-bundle/2"
ACCEPTED_FORMATS = (BUNDLE_FORMAT_V1, BUNDLE_FORMAT)

PROVENANCE_PRESENT = "present"
PROVENANCE_ABSENT = "absent"

FORMAT_MISMATCH = "FORMAT-MISMATCH"
COUNT_MISMATCH = "COUNT-MISMATCH"
PARSE_ERROR = "PARSE-ERROR"

# Which break code a bundle state exits on. 0 clean, 1 findings, 2 could-not-check —
# the same discipline `audit` and `provenance` already use.
EXIT_FOR_STATE = {PASS: 0, MISMATCH: 1, UNMEASURABLE: 2, ABSENT: 2}

Bindings = Union[Mapping[int, Binding], Sequence[Binding], None]


class ExportError(Exception):
    """Raised when a bundle cannot be written or read."""


@dataclass(frozen=True)
class BundleReport:
    """The chain verdict, both provenance legs, and one state to script against."""

    ok: bool
    state: str
    checked: int
    head_hash: str
    breaks: Tuple[Break, ...] = ()
    bindings: Tuple[BindingCheck, ...] = ()
    proof: Optional[Proof] = None

    @property
    def exit_code(self) -> int:
        return EXIT_FOR_STATE.get(self.state, 2)

    def to_dict(self) -> dict:
        payload = {
            "ok": self.ok,
            "state": self.state,
            "checked": self.checked,
            "head_hash": self.head_hash,
            "breaks": [
                {"code": brk.code, "seq": brk.seq, "detail": brk.detail}
                for brk in self.breaks
            ],
            "bindings": [check.to_dict() for check in self.bindings],
        }
        if self.proof is not None:
            payload["provenance"] = self.proof.to_dict()
            payload["audit"] = dict(self.proof.recomputed)
        return payload


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ordered(bindings: Bindings) -> Optional[Sequence[Binding]]:
    """Bindings in seq order, or None when the caller deliberately travels none.

    None and "empty" are different answers: None means the exporter chose not to carry
    provenance (an incomplete bundle that says so), while an empty sequence means the
    ledger had nothing bound.
    """
    if bindings is None:
        return None
    if isinstance(bindings, Mapping):
        return [bindings[seq] for seq in sorted(bindings)]
    return sorted(bindings, key=lambda binding: binding.seq)


def binding_payload(binding: Binding) -> dict:
    """One binding as it travels: never the exporting machine's abspath.

    A path to `/home/someone/models/x.json` is not evidence on the receiving machine, and
    carrying it would make the bundle non-self-contained. The basename is what survives a
    move; the fingerprint is what makes the claim re-measurable where the file does exist.
    """
    return {
        "seq": int(binding.seq),
        "model_digest": binding.model_digest,
        "format": binding.format,
        "tensor_count": binding.tensor_count,
        "manifest_sha256": binding.manifest_sha256,
        "manifest_basename": binding.manifest_basename,
        "recorded_at": binding.recorded_at,
    }


def build_bundle(entries: Sequence[Entry], bindings: Bindings = None,
                 generated_at: Optional[str] = None) -> dict:
    """A bundle that says what it can prove and what it cannot.

    `bindings=None` is the deliberate chain-only export: it writes `provenance: absent`
    and a null binding list into the file rather than leaving a reader to notice the gap.
    """
    entries = list(entries)
    ordered = _ordered(bindings)
    payloads = None if ordered is None else [binding_payload(binding) for binding in ordered]
    digest_map = {} if ordered is None else {binding.seq: binding.model_digest for binding in ordered}
    declared = audit(entries, digest_map)
    return {
        "format": BUNDLE_FORMAT,
        "generated_at": generated_at or _now(),
        "provenance": PROVENANCE_ABSENT if payloads is None else PROVENANCE_PRESENT,
        "count": len(entries),
        "head_hash": entries[-1].hash if entries else "0" * 64,
        "entries": [entry.to_dict() for entry in entries],
        "bindings": payloads,
        "audit": declared.to_dict(),
    }


def bundle_digest(bundle: dict) -> str:
    """Digest of the evidence only — `generated_at` is metadata, not evidence.

    The bindings are evidence: they are the half of the trust base that says a digest was
    derived. Excluding them would let a binding be rewritten under a stable digest.
    """
    return sha256_hex(
        canonical_json(
            {
                "count": bundle.get("count"),
                "head_hash": bundle.get("head_hash"),
                "entries": bundle.get("entries", []),
                "bindings": bundle.get("bindings"),
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


def _chain_state(chain: VerificationResult, breaks: Sequence[Break]) -> str:
    return PASS if chain.ok and not breaks else MISMATCH


def verify_bundle(bundle: dict) -> BundleReport:
    """Verify the chain, then the two legs that used to be missing from the artifact."""
    breaks = []
    fmt = bundle.get("format")
    if fmt not in ACCEPTED_FORMATS:
        breaks.append(
            Break(
                FORMAT_MISMATCH,
                0,
                "bundle format %r is not one of %s"
                % (fmt, ", ".join(repr(name) for name in ACCEPTED_FORMATS)),
            )
        )

    entries = []
    for position, payload in enumerate(bundle.get("entries") or ()):
        try:
            entries.append(Entry.from_dict(payload))
        except (KeyError, TypeError, ValueError) as exc:
            breaks.append(Break(PARSE_ERROR, position, "entry %d is malformed: %s" % (position, exc)))

    declared_count = bundle.get("count")
    if declared_count != len(entries):
        breaks.append(
            Break(
                COUNT_MISMATCH,
                0,
                "bundle declares %s record(s) but carries %d (a record was dropped)"
                % (declared_count, len(entries)),
            )
        )

    chain = verify_entries(entries, expected_head=bundle.get("head_hash"))

    # A v1 bundle predates bindings entirely: absent, not empty.
    checkable = fmt == BUNDLE_FORMAT
    proof = prove(
        entries,
        bundle.get("bindings") if checkable else None,
        bundle.get("audit"),
        checkable=checkable,
    )

    findings = tuple(
        Break(finding.code, finding.seq, finding.detail) for finding in proof.findings
    )
    all_breaks = tuple(breaks) + chain.breaks + findings

    chain_state = _chain_state(chain, breaks)
    state = MISMATCH if chain_state == MISMATCH else proof.state
    return BundleReport(
        ok=chain_state == PASS and proof.state == PASS,
        state=state,
        checked=chain.checked,
        head_hash=chain.head_hash,
        breaks=all_breaks,
        bindings=proof.checks,
        proof=proof,
    )
