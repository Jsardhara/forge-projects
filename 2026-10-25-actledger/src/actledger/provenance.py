"""Re-measure the manifest a bound digest came from.

`append_binding` records `format`, `tensor_count`, `manifest_sha256` and the manifest
path beside the ledger. Until this module existed, nothing read those four fields back:
`audit` asked only "is there a binding that names this digest", so a MEASURED row
carried provenance claims whose truth was never checked, and a ledger moved to another
machine recorded an abspath that means nothing there.

Three states, never two:

* PASS          the manifest at the recorded location still fingerprints to the value
                recorded when the digest was derived;
* MISMATCH      it does not - the file was edited after the binding was written;
* UNMEASURABLE  the file is gone, unreadable, or the binding predates the fingerprint -
                which is not a pass, because "could not check" and "checked and fine"
                are different answers.

A binding written before this change carries no `manifest_sha256`. It is reported
UNMEASURABLE rather than assumed good: the fingerprint was never taken, so there is
nothing to compare against.
"""

import json
import os
from dataclasses import dataclass
from typing import Any, Mapping, Optional, Sequence, Tuple

from .manifest import Binding, manifest_sha256
from .models import AuditFinding, Severity

PASS = "PASS"
MISMATCH = "MISMATCH"
UNMEASURABLE = "UNMEASURABLE"

SHA_MISMATCH_CODE = "MANIFEST-SHA-MISMATCH"
UNMEASURABLE_CODE = "MANIFEST-UNMEASURABLE"


@dataclass(frozen=True)
class ManifestCheck:
    """What happened when one bound row's manifest was re-measured."""

    seq: int
    state: str
    manifest: str = ""
    resolved_by: str = "none"
    detail: str = ""

    def to_dict(self) -> dict:
        return {
            "seq": self.seq,
            "state": self.state,
            "manifest": self.manifest,
            "resolved_by": self.resolved_by,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class ProvenanceReport:
    checked: int
    passed: int
    mismatched: int
    unmeasurable: int
    checks: Tuple[ManifestCheck, ...] = ()
    findings: Tuple[AuditFinding, ...] = ()

    @property
    def ok(self) -> bool:
        """True only when every checked row passed - an unmeasurable row is not ok."""
        return self.mismatched == 0 and self.unmeasurable == 0

    def to_dict(self) -> dict:
        return {
            "checked": self.checked,
            "passed": self.passed,
            "mismatched": self.mismatched,
            "unmeasurable": self.unmeasurable,
            "ok": self.ok,
            "checks": [check.to_dict() for check in self.checks],
        }


def _resolve(binding: Binding, ledger_path: str) -> Tuple[str, str]:
    """The manifest to read, and how it was found.

    The recorded abspath is authoritative on the machine that wrote the ledger. A
    ledger that moved carries the basename instead - so look beside the ledger before
    declaring the manifest lost. Never search the wider filesystem: a same-named file
    found somewhere else is not the same measurement.
    """
    if binding.manifest and os.path.isfile(binding.manifest):
        return binding.manifest, "path"
    if binding.manifest_basename:
        beside = os.path.join(
            os.path.dirname(os.path.abspath(ledger_path)), binding.manifest_basename
        )
        if os.path.isfile(beside):
            return beside, "basename"
    return "", "none"


def _read_payload(path: str) -> Optional[Mapping[str, Any]]:
    """The manifest as JSON, or None when it cannot be read as a JSON object."""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, ValueError):
        return None
    return payload if isinstance(payload, dict) else None


def _check_one(seq: int, binding: Binding, ledger_path: str) -> ManifestCheck:
    if not binding.manifest_sha256:
        return ManifestCheck(
            seq=seq,
            state=UNMEASURABLE,
            manifest=binding.manifest,
            detail=(
                "seq %d binds digest %s but records no manifest_sha256 - the provenance "
                "of this row was never fingerprinted, so it cannot be re-measured"
                % (seq, binding.model_digest[:20])
            ),
        )

    path, resolved_by = _resolve(binding, ledger_path)
    if not path:
        return ManifestCheck(
            seq=seq,
            state=UNMEASURABLE,
            manifest=binding.manifest,
            detail=(
                "seq %d: manifest %s is not on disk and no %r sits beside the ledger - "
                "the binding points at a measurement nobody can re-run"
                % (seq, binding.manifest or "(no path recorded)", binding.manifest_basename)
            ),
        )

    payload = _read_payload(path)
    if payload is None:
        return ManifestCheck(
            seq=seq,
            state=UNMEASURABLE,
            manifest=path,
            resolved_by=resolved_by,
            detail="seq %d: manifest %s is unreadable or not a JSON object" % (seq, path),
        )

    recomputed = manifest_sha256(payload)
    if recomputed != binding.manifest_sha256:
        return ManifestCheck(
            seq=seq,
            state=MISMATCH,
            manifest=path,
            resolved_by=resolved_by,
            detail=(
                "seq %d: manifest %s was edited after its digest was bound - recorded %s, "
                "now %s" % (seq, path, binding.manifest_sha256[:16], recomputed[:16])
            ),
        )

    return ManifestCheck(
        seq=seq,
        state=PASS,
        manifest=path,
        resolved_by=resolved_by,
        detail="seq %d: manifest %s matches its recorded fingerprint" % (seq, path),
    )


def _finding(check: ManifestCheck) -> Optional[AuditFinding]:
    if check.state == MISMATCH:
        return AuditFinding(
            code=SHA_MISMATCH_CODE, severity=Severity.FLAG, detail=check.detail, seq=check.seq
        )
    if check.state == UNMEASURABLE:
        return AuditFinding(
            code=UNMEASURABLE_CODE, severity=Severity.WARN, detail=check.detail, seq=check.seq
        )
    return None


def check_bindings(entries: Sequence, bindings: Optional[Mapping[int, Binding]],
                   ledger_path: str) -> ProvenanceReport:
    """Re-measure every MEASURED row's manifest.

    Only rows whose recorded digest equals the digest in their binding are checked -
    everything else is already `audit`'s AAL-007 and would be double-reported here.
    """
    checks = []
    findings = []
    for entry in entries:
        binding = (bindings or {}).get(entry.seq)
        if binding is None or binding.model_digest != entry.record.model_digest:
            continue
        check = _check_one(entry.seq, binding, ledger_path)
        checks.append(check)
        finding = _finding(check)
        if finding is not None:
            findings.append(finding)

    return ProvenanceReport(
        checked=len(checks),
        passed=sum(1 for check in checks if check.state == PASS),
        mismatched=sum(1 for check in checks if check.state == MISMATCH),
        unmeasurable=sum(1 for check in checks if check.state == UNMEASURABLE),
        checks=tuple(checks),
        findings=tuple(findings),
    )