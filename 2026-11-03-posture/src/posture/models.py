"""Value types shared by every stage. Immutable; nothing here is mutated in place."""

from dataclasses import dataclass, replace
from typing import Optional

CLEAN = "clean"
FINDINGS = "findings"
UNMEASURABLE = "unmeasurable"
ERROR = "error"

#: Worst-first ordering. Used only for display and for picking the run's headline.
SEVERITY_RANK = {CLEAN: 0, FINDINGS: 1, UNMEASURABLE: 2, ERROR: 3}


def status_for_exit(code: Optional[int]) -> str:
    """Map a verifier's exit code to a posture status.

    The repo-wide contract is 0/1/2. Anything else — a shell's 127, a signal, a
    missing code — is a broken verifier, not a finding. Fail closed: unknown is
    never clean.
    """
    if code == 0:
        return CLEAN
    if code == 1:
        return FINDINGS
    if code == 2:
        return UNMEASURABLE
    return ERROR


@dataclass(frozen=True)
class VerifierResult:
    """One verifier, one run. Holds a digest, never the output itself."""

    name: str
    status: str
    exit_code: Optional[int]
    duration_s: float
    digest: str
    error: Optional[str] = None

    @property
    def measured(self) -> bool:
        return self.status in (CLEAN, FINDINGS)

    @property
    def needs_human(self) -> bool:
        return self.status != CLEAN

    @property
    def rank(self) -> int:
        return SEVERITY_RANK[self.status]

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "status": self.status,
            "exit_code": self.exit_code,
            "duration_s": round(self.duration_s, 3),
            "digest": self.digest,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, row: dict) -> "VerifierResult":
        return cls(
            name=str(row.get("name", "")),
            status=str(row.get("status", ERROR)),
            exit_code=row.get("exit_code"),
            duration_s=float(row.get("duration_s", 0.0)),
            digest=str(row.get("digest", "")),
            error=row.get("error"),
        )

    def with_status(self, status: str, error: Optional[str] = None) -> "VerifierResult":
        return replace(self, status=status, error=error)


@dataclass(frozen=True)
class Transition:
    """A change worth telling a human about. Insertion-ordered for stable output."""

    name: str
    field: str  # status | signal | appeared | vanished
    before: str
    after: str

    def describe(self) -> str:
        if self.field in ("appeared", "vanished"):
            return f"{self.name} {self.field}"
        if self.field == "signal":
            return f"{self.name} output changed (status still {self.after})"
        return f"{self.name} {self.field}: {self.before} -> {self.after}"
