"""Hash chain primitives.

The chain is the evidence. Each entry's hash covers its sequence number, the previous
entry's hash and the canonical form of its record, so any edit, reorder or deletion in
the middle breaks a link that a verifier can point at by sequence number.

Truncation is a different attack and needs a different defence: the last hash is
committed separately (a head sidecar, or the `head_hash` of an exported bundle), and
`verify` compares the chain it walked against that commitment.
"""

import hashlib
import json
from typing import Any, Iterable, List, Optional, Sequence, Tuple

from .models import ActionRecord, Break, Entry, VerificationResult

GENESIS_HASH = "0" * 64

# Break codes. Stable strings: they are what an auditor reads and a CI gate greps.
PARSE_ERROR = "PARSE-ERROR"
SEQ_GAP = "SEQ-GAP"
PREV_MISMATCH = "PREV-MISMATCH"
HASH_MISMATCH = "HASH-MISMATCH"
HEAD_MISMATCH = "HEAD-MISMATCH"


def canonical_json(payload: Any) -> str:
    """Deterministic, ASCII-only JSON. The same object must always hash the same."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def entry_hash(seq: int, prev_hash: str, record_payload: dict) -> str:
    return sha256_hex(
        canonical_json({"seq": seq, "prev_hash": prev_hash, "record": record_payload})
    )


def make_entry(seq: int, prev_hash: str, record: ActionRecord) -> Entry:
    digest = entry_hash(seq, prev_hash, record.to_dict())
    return Entry(seq=seq, record=record, prev_hash=prev_hash, hash=digest)


def _check_entries(entries: Sequence[Entry]) -> List[Break]:
    breaks: List[Break] = []
    expected_prev = GENESIS_HASH
    for position, entry in enumerate(entries):
        if entry.seq != position:
            breaks.append(
                Break(
                    SEQ_GAP,
                    position,
                    "expected seq %d, found %d (a record was removed or reordered)"
                    % (position, entry.seq),
                )
            )
        if entry.prev_hash != expected_prev:
            breaks.append(
                Break(
                    PREV_MISMATCH,
                    position,
                    "prev_hash %s does not match the chain's %s"
                    % (entry.prev_hash[:12], expected_prev[:12]),
                )
            )
        recomputed = entry_hash(entry.seq, entry.prev_hash, entry.record.to_dict())
        if recomputed != entry.hash:
            breaks.append(
                Break(
                    HASH_MISMATCH,
                    position,
                    "record hash %s does not recompute to %s (record was edited)"
                    % (entry.hash[:12], recomputed[:12]),
                )
            )
        expected_prev = entry.hash
    return breaks


def verify_entries(
    entries: Sequence[Entry], expected_head: Optional[str] = None
) -> VerificationResult:
    """Walk the chain. Returns every break, not just the first, so one run is enough."""
    breaks = _check_entries(entries)
    head = entries[-1].hash if entries else GENESIS_HASH

    if expected_head is not None and expected_head != head:
        breaks.append(
            Break(
                HEAD_MISMATCH,
                0 if not entries else len(entries) - 1,
                "chain ends at %s but the committed head is %s (records were truncated)"
                % (head[:12], expected_head[:12]),
            )
        )

    return VerificationResult(
        ok=not breaks, checked=len(entries), breaks=tuple(breaks), head_hash=head
    )


def parse_lines(lines: Iterable[str]) -> Tuple[List[Entry], List[Break]]:
    """Parse JSONL ledger text. A bad line is reported, never raised."""
    entries: List[Entry] = []
    breaks: List[Break] = []
    for number, raw in enumerate(lines):
        stripped = raw.strip()
        if not stripped:
            continue
        try:
            entries.append(Entry.from_dict(json.loads(stripped)))
        except (ValueError, KeyError, TypeError) as exc:
            breaks.append(
                Break(PARSE_ERROR, number, "line %d is not a ledger entry: %s" % (number, exc))
            )
    return entries, breaks


def verify_lines(lines: Iterable[str], expected_head: Optional[str] = None) -> VerificationResult:
    entries, parse_breaks = parse_lines(lines)
    result = verify_entries(entries, expected_head=expected_head)
    if not parse_breaks:
        return result
    return VerificationResult(
        ok=False,
        checked=result.checked,
        breaks=tuple(parse_breaks) + result.breaks,
        head_hash=result.head_hash,
    )
