"""Prove, from a bundle alone, the two legs the bundle exists to carry.

`export.py` says a bundle plus this tool's stdlib code is "the whole trust base". For
immutability that was true. For **responsibility** (AAL-001/002/003) and **provenance**
(AAL-007) it was not: the bundle carried the fields and none of the verdicts, so a
receiver outside the machine held `ws1:...` strings and a `verifier` column with nothing
that could judge either. A typed digest and a derived digest looked identical.

This module is the missing half. Given the bundle's own records, its `bindings` and its
declared `audit`, it recomputes both legs:

* every tagged digest must be corroborated by a binding that names the *identical* digest.
  A binding naming a different digest is `BINDING-MISMATCH` — and this is the forgery
  case, because bindings live outside the hash chain, so a bundle is where it is caught;
* the declared posture must equal the posture the records actually earn. A bundle whose
  `audit` block claims PASS while the records carry an unverified action is
  `AUDIT-DIVERGES` — "declared" is a claim, "recomputed" is a finding;
* a bundle that carries no bindings at all (format v1, or a deliberate `--no-provenance`
  export) is `BINDINGS-ABSENT`: **not checkable, never clean**. An old artifact must not
  read as if it had been checked.

What this cannot do is re-open the manifest — it is not in the bundle, by design. That
leg is named rather than implied: `MANIFEST-NOT-BUNDLED` (INFO) says the fingerprint
travelled but was not re-measured here, and stays checkable with `audit --verify-manifest`
by whoever is also handed the file.
"""

import re
from dataclasses import dataclass
from typing import Any, Mapping, Optional, Sequence, Tuple

from .audit import AuditReport, audit
from .manifest import is_tagged
from .models import AuditFinding, Severity

PASS = "PASS"
MISMATCH = "MISMATCH"
UNMEASURABLE = "UNMEASURABLE"
ABSENT = "BINDINGS-ABSENT"

BINDING_MISMATCH = "BINDING-MISMATCH"
BINDING_UNMEASURABLE = "BINDING-UNMEASURABLE"
BINDING_ORPHAN = "BINDING-ORPHAN"
BINDING_DUPLICATE = "BINDING-DUPLICATE"
ABSENT_CODE = "BINDINGS-ABSENT"
AUDIT_DIVERGES = "AUDIT-DIVERGES"
AUDIT_ABSENT = "AUDIT-ABSENT"
MANIFEST_NOT_BUNDLED = "MANIFEST-NOT-BUNDLED"

_HEX64 = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class BindingCheck:
    """What one recorded `ws1:` digest could be corroborated against inside the bundle."""

    seq: int
    state: str
    digest: str = ""
    manifest: str = ""
    detail: str = ""

    def to_dict(self) -> dict:
        return {
            "seq": self.seq,
            "state": self.state,
            "digest": self.digest,
            "manifest": self.manifest,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class Proof:
    """Both legs, and the single state a receiver scripts against."""

    state: str
    checks: Tuple[BindingCheck, ...]
    findings: Tuple[AuditFinding, ...]
    recomputed: Mapping[str, Any]
    declared_present: bool
    declared: Optional[Mapping[str, Any]] = None

    @property
    def corroborated(self) -> int:
        return sum(1 for check in self.checks if check.state == PASS)

    @property
    def mismatched(self) -> int:
        return sum(1 for check in self.checks if check.state == MISMATCH)

    @property
    def unmeasurable(self) -> int:
        return sum(1 for check in self.checks if check.state == UNMEASURABLE)

    def to_dict(self) -> dict:
        return {
            "state": self.state,
            "corroborated": self.corroborated,
            "mismatched": self.mismatched,
            "unmeasurable": self.unmeasurable,
            "declared_present": self.declared_present,
            "checks": [check.to_dict() for check in self.checks],
        }


def _digest_map(payloads: Sequence[Any]) -> dict:
    """seq -> declared digest, for recomputing the audit exactly as the exporter did."""
    return {
        payload["seq"]: payload["model_digest"]
        for payload in payloads
        if isinstance(payload, Mapping)
        and isinstance(payload.get("seq"), int)
        and not isinstance(payload.get("seq"), bool)
        and isinstance(payload.get("model_digest"), str)
    }


def _collect(payloads: Sequence[Any]) -> Tuple[dict, list]:
    """Index the bundle's bindings, keeping every defect instead of raising on it.

    The bundle is attacker-reachable, so a malformed binding must become a finding. A
    parser that raises here would turn a forged artifact into a crash, which a caller
    can mistake for "unreadable" rather than "tampered with".
    """
    indexed = {}
    findings = []
    for position, payload in enumerate(payloads or ()):
        if not isinstance(payload, Mapping):
            findings.append(
                AuditFinding(
                    code=BINDING_MISMATCH,
                    severity=Severity.FLAG,
                    detail="binding %d is not an object - the artifact is malformed" % position,
                )
            )
            continue
        seq = payload.get("seq")
        digest = payload.get("model_digest")
        if not isinstance(seq, int) or isinstance(seq, bool) or not isinstance(digest, str):
            findings.append(
                AuditFinding(
                    code=BINDING_MISMATCH,
                    severity=Severity.FLAG,
                    detail="binding %d has no integer seq / string digest - malformed" % position,
                )
            )
            continue
        if seq in indexed:
            findings.append(
                AuditFinding(
                    code=BINDING_DUPLICATE,
                    severity=Severity.FLAG,
                    detail="bundle binds seq %d twice - one seq is bound once" % seq,
                    seq=seq,
                )
            )
            continue
        indexed[seq] = payload
    return indexed, findings


def _check_row(seq: int, digest: str, payload: Optional[Mapping[str, Any]]) -> BindingCheck:
    if payload is None:
        return BindingCheck(
            seq=seq,
            state=UNMEASURABLE,
            digest=digest,
            detail=(
                "seq %d carries digest %s but the bundle travels no binding for it - a "
                "digest that travelled without its derivation cannot be told apart from "
                "a typed one" % (seq, digest[:20])
            ),
        )

    stated = str(payload.get("model_digest") or "")
    if stated != digest:
        return BindingCheck(
            seq=seq,
            state=MISMATCH,
            digest=digest,
            detail=(
                "seq %d: the record says %s and the binding carried beside it says %s - "
                "the digest in the bundle was not the one a tool derived"
                % (seq, digest[:20], stated[:20] or "(nothing)")
            ),
        )

    fingerprint = str(payload.get("manifest_sha256") or "").lower()
    basename = str(payload.get("manifest_basename") or "")
    if not fingerprint:
        return BindingCheck(
            seq=seq,
            state=UNMEASURABLE,
            digest=digest,
            manifest=basename,
            detail=(
                "seq %d: the binding records no manifest fingerprint - its provenance was "
                "never taken, so there is nothing for a receiver to re-measure" % seq
            ),
        )
    if not _HEX64.match(fingerprint):
        return BindingCheck(
            seq=seq,
            state=MISMATCH,
            digest=digest,
            manifest=basename,
            detail=(
                "seq %d: the recorded manifest fingerprint is not a sha256 - the binding "
                "was edited after it was written" % seq
            ),
        )

    return BindingCheck(
        seq=seq,
        state=PASS,
        digest=digest,
        manifest=basename,
        detail=(
            "seq %d: digest corroborated by its binding, manifest %s fingerprinted %s"
            % (seq, basename or "(unnamed)", fingerprint[:16])
        ),
    )


def _finding(check: BindingCheck) -> Optional[AuditFinding]:
    if check.state == MISMATCH:
        return AuditFinding(
            code=BINDING_MISMATCH, severity=Severity.FLAG, detail=check.detail, seq=check.seq
        )
    if check.state == UNMEASURABLE:
        return AuditFinding(
            code=BINDING_UNMEASURABLE,
            severity=Severity.WARN,
            detail=check.detail,
            seq=check.seq,
        )
    return None


def _audit_findings(declared: Optional[Mapping[str, Any]],
                    recomputed: AuditReport) -> Tuple[AuditFinding, ...]:
    """The declared posture must be the posture these records earn."""
    if not isinstance(declared, Mapping):
        return (
            AuditFinding(
                code=AUDIT_ABSENT,
                severity=Severity.WARN,
                detail=(
                    "the bundle carries no declared audit - a receiver can recompute the "
                    "posture but cannot tell what the exporter claimed"
                ),
            ),
        )

    earned = recomputed.to_dict()
    differences = []
    for field in ("total", "unverified", "independent_verified", "severity"):
        if declared.get(field) != earned[field]:
            differences.append("%s declared %r, records earn %r"
                               % (field, declared.get(field), earned[field]))

    declared_codes = sorted(
        (str(item.get("code")), item.get("seq"))
        for item in declared.get("findings") or ()
        if isinstance(item, Mapping)
    )
    earned_codes = sorted((finding.code, finding.seq) for finding in recomputed.findings)
    if declared_codes != earned_codes:
        differences.append(
            "findings declared %s, records earn %s"
            % ([code for code, _ in declared_codes], [code for code, _ in earned_codes])
        )

    if not differences:
        return ()
    return (
        AuditFinding(
            code=AUDIT_DIVERGES,
            severity=Severity.FLAG,
            detail="the posture written into the bundle is not the one its records earn: %s"
            % "; ".join(differences),
        ),
    )


def prove(entries: Sequence, payloads: Optional[Sequence[Any]],
          declared: Optional[Mapping[str, Any]], checkable: bool) -> Proof:
    """Both legs, from the artifact alone.

    `checkable` is False for a format-v1 bundle; a v2 bundle that deliberately exported
    no bindings passes `payloads=None` and is treated the same way — absent, not clean.
    """
    if not checkable or payloads is None:
        recomputed = audit(entries, None)
        findings = (
            AuditFinding(
                code=ABSENT_CODE,
                severity=Severity.WARN,
                detail=(
                    "this bundle carries no bindings: its digests cannot be told apart "
                    "from transcriptions and its posture cannot be reproduced. Not "
                    "checkable here - which is not the same answer as clean"
                ),
            ),
        ) + _audit_findings(declared, recomputed)
        return Proof(
            state=ABSENT,
            checks=(),
            findings=findings,
            recomputed=recomputed.to_dict(),
            declared_present=isinstance(declared, Mapping),
            declared=declared if isinstance(declared, Mapping) else None,
        )

    indexed, findings = _collect(payloads)
    checks = []
    for entry in entries:
        digest = entry.record.model_digest.strip()
        if not is_tagged(digest):
            continue
        check = _check_row(entry.seq, digest, indexed.get(entry.seq))
        checks.append(check)
        finding = _finding(check)
        if finding is not None:
            findings.append(finding)
        indexed.pop(entry.seq, None)

    for seq in sorted(indexed):
        findings.append(
            AuditFinding(
                code=BINDING_ORPHAN,
                severity=Severity.FLAG,
                detail=(
                    "the bundle binds seq %d, which is not a row carrying a model digest - "
                    "a binding for a row that is not here is not evidence of anything" % seq
                ),
                seq=seq,
            )
        )

    recomputed = audit(entries, _digest_map(payloads))
    audit_findings = _audit_findings(declared, recomputed)
    findings.extend(audit_findings)

    if checks and any(check.manifest for check in checks):
        findings.append(
            AuditFinding(
                code=MANIFEST_NOT_BUNDLED,
                severity=Severity.INFO,
                detail=(
                    "manifest fingerprints travelled with the artifact but were not "
                    "re-measured here: the manifest is not in the bundle. Re-measure it "
                    "with 'audit --verify-manifest' if you were handed the file"
                ),
            )
        )

    if any(finding.severity is Severity.FLAG for finding in findings):
        state = MISMATCH
    elif any(finding.code == AUDIT_ABSENT for finding in findings) or any(
        check.state == UNMEASURABLE for check in checks
    ):
        state = UNMEASURABLE
    else:
        state = PASS

    return Proof(
        state=state,
        checks=tuple(checks),
        findings=tuple(findings),
        recomputed=recomputed.to_dict(),
        declared_present=isinstance(declared, Mapping),
        declared=declared if isinstance(declared, Mapping) else None,
    )
