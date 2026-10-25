"""File-backed append-only ledger.

Two files, deliberately:

* `<ledger>.jsonl` — one hash-chained entry per line, append-only in practice.
* `<ledger>.head.json` — the committed `{count, head_hash}`.

The head file is what makes truncation detectable. An attacker with write access to a
ledger file can always delete the tail; they cannot (in one atomic write) also produce a
fresh head that a verifier was already told to expect.

Append refuses to run when the file and the head disagree. A ledger that has drifted is
evidence of tampering, and silently extending it would launder that fact into a clean
chain — the exact silent-death mode this tool exists to prevent.
"""

import json
import os
import tempfile
from typing import List, Tuple

from .chain import GENESIS_HASH, make_entry, parse_lines, verify_entries, verify_lines
from .models import ActionRecord, Entry, VerificationResult


class LedgerError(Exception):
    """Raised for a ledger that cannot be trusted or cannot be written."""


class Ledger:
    def __init__(self, path: str) -> None:
        self.path = path
        self.head_path = path + ".head.json"

    # -- reading -----------------------------------------------------------

    def exists(self) -> bool:
        return os.path.exists(self.path)

    def read_lines(self) -> List[str]:
        if not self.exists():
            raise LedgerError("no such ledger: %s" % self.path)
        with open(self.path, "r", encoding="utf-8") as handle:
            return handle.read().splitlines()

    def entries(self) -> List[Entry]:
        entries, breaks = parse_lines(self.read_lines())
        if breaks:
            raise LedgerError(
                "%d unreadable line(s) in %s (first: %s)"
                % (len(breaks), self.path, breaks[0].detail)
            )
        return entries

    def head(self) -> Tuple[int, str]:
        """The committed head. Absent sidecar means nothing has been committed yet."""
        if not os.path.exists(self.head_path):
            return (0, GENESIS_HASH)
        with open(self.head_path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        return (int(payload["count"]), str(payload["head_hash"]))

    # -- writing -----------------------------------------------------------

    def append(self, record: ActionRecord) -> Entry:
        directory = os.path.dirname(os.path.abspath(self.path))
        if not os.path.isdir(directory):
            raise LedgerError("ledger directory does not exist: %s" % directory)

        count, committed_head = self.head()
        existing = self.entries() if self.exists() else []

        if len(existing) != count:
            raise LedgerError(
                "ledger drift in %s: %d record(s) on disk, head commits %d — refusing to "
                "append onto a chain that has been modified" % (self.path, len(existing), count)
            )
        current = verify_entries(existing, expected_head=committed_head)
        if not current.ok:
            raise LedgerError(
                "refusing to append to a broken chain (%s at seq %d): %s"
                % (
                    current.breaks[0].code,
                    current.breaks[0].seq,
                    current.breaks[0].detail,
                )
            )

        entry = make_entry(count, committed_head, record)
        with open(self.path, "a", encoding="utf-8") as handle:
            handle.write(entry.to_json_line() + "\n")
            handle.flush()
            os.fsync(handle.fileno())

        self._commit_head(count + 1, entry.hash)
        return entry

    def _commit_head(self, count: int, head_hash: str) -> None:
        directory = os.path.dirname(os.path.abspath(self.head_path))
        handle = tempfile.NamedTemporaryFile(
            "w", dir=directory, prefix=".head-", suffix=".tmp", delete=False, encoding="utf-8"
        )
        try:
            json.dump({"count": count, "head_hash": head_hash}, handle, sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
        finally:
            handle.close()
        os.replace(handle.name, self.head_path)

    # -- verifying ---------------------------------------------------------

    def verify(self) -> VerificationResult:
        lines = self.read_lines()
        expected = self.head()[1] if os.path.exists(self.head_path) else None  # Optional[str]
        return verify_lines(lines, expected_head=expected)
