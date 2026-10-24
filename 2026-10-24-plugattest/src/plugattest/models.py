"""Core value objects: severity, findings, and the attestation report."""

from dataclasses import dataclass, field
from enum import Enum


class Severity(Enum):
    """Ordered severity. Rank lives in SEVERITY_RANK, never in .value ordering."""

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

# Magnitude weights, used ONLY for the score/gate display. Verdict is
# severity-dominant: the worst single finding decides, never a sum crossing bands.
FINDING_WEIGHTS = {
    "PA-001": 40,  # capability used but not declared
    "PA-002": 0,   # declared but unused (informational)
    "PA-003": 25,  # manifest present, no capability claim at all
    "PA-004": 50,  # auto-execution hook not declared
    "PA-005": 60,  # no manifest at all yet capabilities are used
    "PA-006": 15,  # declared capability token is not a known capability
    "PA-007": 20,  # manifest exists but could not be parsed
}

SCORE_CAP = 100


@dataclass(frozen=True)
class Finding:
    """One attestation finding. Immutable."""

    code: str
    severity: Severity
    location: str
    message: str
    capability: str = ""

    def to_dict(self):
        return {
            "code": self.code,
            "severity": self.severity.value,
            "location": self.location,
            "message": self.message,
            "capability": self.capability,
        }


def worst_severity(severities):
    """Return the highest-ranked severity, or PASS when the sequence is empty."""
    worst = Severity.PASS
    for severity in severities:
        if SEVERITY_RANK[severity] > SEVERITY_RANK[worst]:
            worst = severity
    return worst


def score_findings(findings):
    """Capped sum of finding weights, 0-100."""
    total = 0
    for finding in findings:
        total += FINDING_WEIGHTS.get(finding.code, 0)
    return min(total, SCORE_CAP)


@dataclass(frozen=True)
class Report:
    """Attestation result for one package. Immutable."""

    package: str
    declared: tuple
    detected: tuple
    findings: tuple = field(default_factory=tuple)

    @property
    def verdict(self):
        return worst_severity(f.severity for f in self.findings)

    @property
    def score(self):
        return score_findings(self.findings)

    def to_dict(self):
        return {
            "package": self.package,
            "verdict": self.verdict.value,
            "score": self.score,
            "declared": list(self.declared),
            "detected": list(self.detected),
            "findings": [f.to_dict() for f in self.findings],
        }
