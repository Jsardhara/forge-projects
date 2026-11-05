"""Responsibility audit — the leg the eMudhra incident was missing.

A chain proves the record was not altered. It says nothing about whether anyone was
assigned to check the action. This module answers that: it counts actions with no named
verifier, self-verified actions, and consequential actions with no recorded approval,
then reports the worst single finding as the verdict.
"""

from dataclasses import dataclass
from typing import Mapping, Optional, Sequence, Tuple

from .manifest import is_tagged
from .models import SEVERITY_RANK, ActionRecord, AuditFinding, Severity, worst_severity

# Tool-name fragments that mark a consequential action: it changes the world outside the
# agent's own scratch space, so a human owner must be on the record.
CONSEQUENTIAL_KEYWORDS = (
    "write",
    "delete",
    "remove",
    "exec",
    "shell",
    "publish",
    "post",
    "send",
    "deploy",
    "spend",
    "trade",
    "transfer",
    "push",
    "credential",
    "rotate",
    "merge",
)

FAIL_ON_ORDER = {"NONE": -1, "PASS": 0, "INFO": 1, "WARN": 2, "FLAG": 3}


def is_consequential(tool: str) -> bool:
    lowered = (tool or "").lower()
    return any(keyword in lowered for keyword in CONSEQUENTIAL_KEYWORDS)


@dataclass(frozen=True)
class AuditReport:
    total: int
    unverified: int
    independent_verified: int
    findings: Tuple[AuditFinding, ...]
    severity: Severity

    def acceptable(self, fail_on: str = "FLAG") -> bool:
        """`--fail-on WARN` fails on WARN or worse; `--fail-on NONE` never fails."""
        threshold = fail_on.upper()
        if threshold == "NONE":
            return True
        return SEVERITY_RANK[self.severity] < SEVERITY_RANK[Severity(threshold)]

    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "unverified": self.unverified,
            "independent_verified": self.independent_verified,
            "severity": self.severity.value,
            "findings": [
                {
                    "code": finding.code,
                    "severity": finding.severity.value,
                    "seq": finding.seq,
                    "detail": finding.detail,
                }
                for finding in self.findings
            ],
        }


def _digest_is_measured(seq: int, record: ActionRecord,
                        bindings: Optional[Mapping[int, str]]) -> bool:
    """A digest is measured only when a tool-derived binding matches it exactly.

    The `ws1:` prefix is not evidence on its own - anyone can type it - so the binding
    line beside the ledger is what is checked, and it must name the same digest.
    """
    if not bindings or not is_tagged(record.model_digest):
        return False
    return bindings.get(seq) == record.model_digest


def _record_findings(seq: int, record: ActionRecord,
                     bindings: Optional[Mapping[int, str]] = None) -> Tuple[AuditFinding, ...]:
    findings = []

    if not record.verifier.strip():
        findings.append(
            AuditFinding(
                code="AAL-001",
                severity=Severity.FLAG,
                detail="%s on '%s' has no named verifier — nobody was assigned to check it"
                % (record.agent_id, record.tool),
                seq=seq,
            )
        )
    elif record.verifier.strip().lower() == record.agent_id.strip().lower():
        findings.append(
            AuditFinding(
                code="AAL-003",
                severity=Severity.WARN,
                detail="%s verified its own action on '%s' — not independent"
                % (record.agent_id, record.tool),
                seq=seq,
            )
        )

    if is_consequential(record.tool):
        if not (record.approved_by.strip() and record.approved_at.strip()):
            findings.append(
                AuditFinding(
                    code="AAL-002",
                    severity=Severity.FLAG,
                    detail="consequential action '%s' has no recorded approval (who + when)"
                    % record.tool,
                    seq=seq,
                )
            )

    if not (record.model_id.strip() and record.model_digest.strip()):
        findings.append(
            AuditFinding(
                code="AAL-004",
                severity=Severity.WARN,
                detail="action on '%s' cannot be tied to a model and weights digest"
                % record.tool,
                seq=seq,
            )
        )
    elif not _digest_is_measured(seq, record, bindings):
        findings.append(
            AuditFinding(
                code="AAL-007",
                severity=Severity.WARN,
                detail=(
                    "MODEL-DIGEST-UNMEASURED: action on '%s' declares digest %s but no "
                    "manifest binding exists for seq %d - a typed digest is a "
                    "transcription, not evidence"
                    % (record.tool, record.model_digest[:20], seq)
                ),
                seq=seq,
            )
        )

    if not record.policy_version.strip():
        findings.append(
            AuditFinding(
                code="AAL-005",
                severity=Severity.WARN,
                detail="action on '%s' carries no policy version" % record.tool,
                seq=seq,
            )
        )

    return tuple(findings)


def audit(entries: Sequence, bindings: Optional[Mapping[int, str]] = None) -> AuditReport:
    findings = []
    for entry in entries:
        findings.extend(_record_findings(entry.seq, entry.record, bindings))

    unverified = sum(1 for entry in entries if not entry.record.verifier.strip())
    independent = sum(
        1
        for entry in entries
        if entry.record.verifier.strip()
        and entry.record.verifier.strip().lower() != entry.record.agent_id.strip().lower()
    )

    if entries and unverified == 0:
        findings.append(
            AuditFinding(
                code="AAL-006",
                severity=Severity.PASS,
                detail="every action in the ledger names an assigned verifier",
                seq=-1,
            )
        )

    ordered = tuple(findings)
    return AuditReport(
        total=len(entries),
        unverified=unverified,
        independent_verified=independent,
        findings=ordered,
        severity=worst_severity(ordered),
    )
