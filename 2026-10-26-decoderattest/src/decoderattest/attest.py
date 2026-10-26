"""Turn raw inventory records into attested findings.

The verdict is severity-dominant: the worst single finding decides, and nothing is
ever promoted because several mild findings stack. A machine running six clean
runtimes and one affected decoder is exposed, not "mostly fine".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .rules import (
    STATUS_AFFECTED,
    STATUS_UNKNOWN,
    Evaluation,
    RuleSet,
)
from .vendored import VendoredCopy

__all__ = ["Finding", "Attestation", "attest", "severity_for", "VERDICT_ORDER"]

SEVERITY_CRITICAL = "CRITICAL"
SEVERITY_WARN = "WARN"
SEVERITY_OK = "OK"

_SEVERITY = {
    STATUS_AFFECTED: SEVERITY_CRITICAL,
    STATUS_UNKNOWN: SEVERITY_WARN,
    "patched": SEVERITY_OK,
    "not_affected": SEVERITY_OK,
}

_RANK = {SEVERITY_CRITICAL: 0, SEVERITY_WARN: 1, SEVERITY_OK: 2}

VERDICT_ORDER = ("EXPOSED", "UNKNOWN", "CLEAN")


def severity_for(status: str) -> str:
    return _SEVERITY.get(status, SEVERITY_WARN)


@dataclass(frozen=True)
class Finding:
    ecosystem: str
    target: str
    version: Optional[str]
    status: str
    severity: str
    reason: str
    fix_hint: Optional[str] = None
    note: str = ""
    evidence: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "ecosystem": self.ecosystem,
            "target": self.target,
            "version": self.version,
            "status": self.status,
            "severity": self.severity,
            "reason": self.reason,
            "fix": self.fix_hint,
            "note": self.note,
            "evidence": dict(self.evidence),
        }


@dataclass(frozen=True)
class Attestation:
    advisory: Dict
    findings: List[Finding]
    notes: List[str]
    counts: Dict[str, int]

    @property
    def verdict(self) -> str:
        if any(finding.severity == SEVERITY_CRITICAL for finding in self.findings):
            return "EXPOSED"
        if any(finding.severity == SEVERITY_WARN for finding in self.findings):
            return "UNKNOWN"
        return "CLEAN"

    @property
    def worst(self) -> Optional[Finding]:
        return self.findings[0] if self.findings else None


def attest(rules: RuleSet, nodes, pythons, packages, vendored) -> Attestation:
    findings: List[Finding] = []

    for node in nodes:
        findings.append(_from_evaluation(
            "node", node.path, node.version, rules.evaluate("node", "node", node.version),
            evidence={"binary": node.path},
        ))

    for install in pythons:
        findings.extend(_python_findings(rules, install))

    for package in packages:
        findings.append(_from_evaluation(
            "system", package.name, package.version,
            rules.evaluate("system", package.name, package.version),
            evidence={"manager": package.manager},
        ))

    for copy in vendored:
        findings.append(_vendored_finding(rules, copy))

    findings = [finding for finding in findings if finding is not None]
    findings.sort(key=lambda finding: (_RANK.get(finding.severity, 1), finding.target))
    notes = _notes(findings) + _scope_notes(rules, pythons)
    return Attestation(
        advisory=dict(rules.advisory),
        findings=findings,
        notes=notes,
        counts=_counts(findings),
    )


def _scope_notes(rules: RuleSet, pythons) -> List[str]:
    """Say what was asked and found nothing -- an empty branch is not a clean one."""
    if not pythons:
        return []
    with_binding = 0
    for install in pythons:
        for module_name in (install.modules or {}):
            if rules.find("python", module_name) is not None:
                with_binding += 1
                break
    if with_binding:
        return []
    return [
        "python: %d python interpreter(s) probed, %d with a Brotli binding importable "
        "(a clean Python branch means nothing was linked, not that it was patched)"
        % (len(pythons), with_binding)
    ]


def _python_findings(rules: RuleSet, install) -> List[Finding]:
    if install.error:
        return [Finding(
            ecosystem="python",
            target="%s :: probe" % install.path,
            version=None,
            status=STATUS_UNKNOWN,
            severity=SEVERITY_WARN,
            reason=install.error,
            evidence={"interpreter": install.path},
        )]
    findings: List[Finding] = []
    for module_name, details in sorted((install.modules or {}).items()):
        if rules.find("python", module_name) is None:
            continue
        version = (details or {}).get("version")
        evaluation = rules.evaluate("python", module_name, version)
        findings.append(_from_evaluation(
            "python",
            "%s :: %s" % (install.path, module_name),
            version,
            evaluation,
            evidence={"file": (details or {}).get("file"), "interpreter": install.path},
        ))
    return findings


def _from_evaluation(ecosystem: str, target: str, version, evaluation: Evaluation,
                     evidence: Optional[Dict] = None) -> Finding:
    return Finding(
        ecosystem=ecosystem,
        target=target,
        version=version,
        status=evaluation.status,
        severity=severity_for(evaluation.status),
        reason=evaluation.reason,
        fix_hint=evaluation.fix_hint,
        note=evaluation.note,
        evidence=dict(evidence or {}),
    )


def _vendored_finding(rules: RuleSet, copy: VendoredCopy) -> Finding:
    evidence = {
        "header": copy.header,
        "version_file": copy.version_file,
        "block_switch": copy.has_block_switch,
        "signals_agree": copy.signals_agree,
    }
    evaluation = _evaluate_vendored(rules, copy)
    return Finding(
        ecosystem="vendored",
        target=copy.header,
        version=copy.version,
        status=evaluation.status,
        severity=severity_for(evaluation.status),
        reason=evaluation.reason,
        fix_hint=evaluation.fix_hint,
        note=evaluation.note,
        evidence=evidence,
    )


def _evaluate_vendored(rules: RuleSet, copy: VendoredCopy) -> Evaluation:
    """Two signals; a disagreement is UNKNOWN, never the safe answer."""
    note = ""
    for product in rules.products:
        if product.id == "vendored" or product.ecosystem == "vendored":
            note = product.note
            break

    if copy.version is None:
        if copy.has_block_switch:
            return Evaluation(
                "patched", "vendored",
                "unversioned copy carries the BLOCK_SWITCH error code the fix introduced",
                "1.2.1", note,
            )
        return Evaluation(
            STATUS_AFFECTED, "vendored",
            "unversioned copy has no BLOCK_SWITCH error code, so it predates the fix",
            "1.2.1", note,
        )

    # A vendored copy *is* the C library, so its version is judged by the same
    # span as the system package -- a second, drifting copy of that rule is how
    # two gates end up disagreeing about the same bytes.
    declared = rules.evaluate("vendored", "brotli", copy.version)
    if declared.status == "not_listed":
        declared = rules.evaluate("system", "brotli", copy.version)

    if declared.status == STATUS_AFFECTED:
        return Evaluation(
            STATUS_AFFECTED, "vendored",
            "declared version %s is affected%s" % (
                copy.version,
                "" if not copy.has_block_switch else " (marker present but version is below the fix)",
            ),
            declared.fix_hint or "1.2.1", note,
        )

    if declared.status == "patched":
        if copy.has_block_switch:
            return Evaluation(
                "patched", "vendored",
                "declared version %s and the BLOCK_SWITCH error code both indicate the fix"
                % copy.version,
                "1.2.1", note,
            )
        return Evaluation(
            STATUS_UNKNOWN, "vendored",
            "declared version %s but no BLOCK_SWITCH error code: signals disagree, "
            "copy cannot be certified" % copy.version,
            "1.2.1", note,
        )

    if declared.status == "not_affected":
        return Evaluation(
            "not_affected", "vendored",
            "declared version %s predates the vulnerable span" % copy.version,
            None, note,
        )

    return Evaluation(
        STATUS_UNKNOWN, "vendored",
        "declared version %s could not be evaluated against the rule file" % copy.version,
        None, note,
    )


def _counts(findings: List[Finding]) -> Dict[str, int]:
    counts = {"found": len(findings), "affected": 0, "patched": 0,
              "not_affected": 0, "unknown": 0}
    for finding in findings:
        counts[finding.status] = counts.get(finding.status, 0) + 1
    return counts


def _notes(findings: List[Finding]) -> List[str]:
    if not findings:
        return [
            "no targets found: nothing on this host could be attested, which is not a pass"
        ]
    notes: List[str] = []
    seen = set()
    for finding in findings:
        if not finding.note or finding.note in seen:
            continue
        seen.add(finding.note)
        notes.append(finding.note)
    return notes
