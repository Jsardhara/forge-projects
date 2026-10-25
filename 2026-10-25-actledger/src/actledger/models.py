"""Immutable value types for the agent action evidence ledger.

Every type here is frozen: a record, once built, cannot be edited in place. The only
way a record changes is by producing a new record, which changes its hash, which breaks
the chain. That property is the product.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Iterable, Tuple


class Severity(Enum):
    """Finding severity. Ordered by an explicit table, never by string comparison."""

    PASS = "PASS"
    INFO = "INFO"
    WARN = "WARN"
    FLAG = "FLAG"


SEVERITY_RANK = {
    Severity.PASS: 0,
    Severity.INFO: 1,
    Severity.WARN: 2,
    Severity.FLAG: 3,
}


@dataclass(frozen=True)
class ActionRecord:
    """One agent action, exactly as it must survive to an auditor.

    `verifier` is the field that does not exist in a normal log: the party assigned to
    check this action. An empty verifier is a real finding, not a missing nicety.
    """

    agent_id: str
    tool: str
    outcome: str
    ts: str = ""
    model_id: str = ""
    model_digest: str = ""
    policy_version: str = ""
    args_hash: str = ""
    data_touched: Tuple[str, ...] = ()
    verifier: str = ""
    approved_by: str = ""
    approved_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "tool": self.tool,
            "outcome": self.outcome,
            "ts": self.ts,
            "model_id": self.model_id,
            "model_digest": self.model_digest,
            "policy_version": self.policy_version,
            "args_hash": self.args_hash,
            "data_touched": list(self.data_touched),
            "verifier": self.verifier,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at,
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "ActionRecord":
        return cls(
            agent_id=payload["agent_id"],
            tool=payload["tool"],
            outcome=payload["outcome"],
            ts=payload.get("ts", ""),
            model_id=payload.get("model_id", ""),
            model_digest=payload.get("model_digest", ""),
            policy_version=payload.get("policy_version", ""),
            args_hash=payload.get("args_hash", ""),
            data_touched=tuple(payload.get("data_touched") or ()),
            verifier=payload.get("verifier", ""),
            approved_by=payload.get("approved_by", ""),
            approved_at=payload.get("approved_at", ""),
        )


@dataclass(frozen=True)
class Entry:
    """A record plus its position in the chain and the hash that binds it."""

    seq: int
    record: ActionRecord
    prev_hash: str
    hash: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "seq": self.seq,
            "record": self.record.to_dict(),
            "prev_hash": self.prev_hash,
            "hash": self.hash,
        }

    def to_json_line(self) -> str:
        from .chain import canonical_json

        return canonical_json(self.to_dict())

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "Entry":
        return cls(
            seq=int(payload["seq"]),
            record=ActionRecord.from_dict(payload["record"]),
            prev_hash=str(payload["prev_hash"]),
            hash=str(payload["hash"]),
        )


@dataclass(frozen=True)
class Break:
    """A single reason the chain does not verify."""

    code: str
    seq: int
    detail: str


@dataclass(frozen=True)
class VerificationResult:
    ok: bool
    checked: int
    breaks: Tuple[Break, ...] = ()
    head_hash: str = ""


@dataclass(frozen=True)
class AuditFinding:
    code: str
    severity: Severity
    detail: str
    seq: int = -1


def worst_severity(findings: Iterable[AuditFinding]) -> Severity:
    """Verdict = the worst single finding. Never ramped up from stacked lesser findings."""
    worst = Severity.PASS
    for finding in findings:
        if SEVERITY_RANK[finding.severity] > SEVERITY_RANK[worst]:
            worst = finding.severity
    return worst
