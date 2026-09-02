"""idguard scanning engine: classify leaked identity assets per record, compute
severity bands, and derive a CI-usable exit gate."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from idguard.patterns import (
    detect_dl,
    detect_dob,
    detect_email,
    detect_phone,
    normalize_ssn,
    validate_ssn,
)

# Exit-code gate: any CRIT -> 2, any HIGH -> 1, else 0.
EXIT_CRITICAL = 2
EXIT_HIGH = 1
EXIT_OK = 0

_SEV_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRIT": 3}


@dataclass
class AssetFinding:
    asset: str
    value: str
    detail: str = ""
    severity: str = ""

    def __str__(self) -> str:  # pragma: no cover - display helper
        return f"{self.asset}:{self.severity}:{self.detail}"


@dataclass
class RecordResult:
    index: int
    findings: List[AssetFinding] = field(default_factory=list)
    present_assets: set = field(default_factory=set)
    severity: str = "LOW"

    def add(self, asset: str, value: str, detail: str = "", severity: str = "LOW"):
        self.findings.append(AssetFinding(asset, value, detail, severity))
        self.present_assets.add(asset)
        if _SEV_ORDER[severity] > _SEV_ORDER[self.severity]:
            self.severity = severity


def _looks_like_name(value: str) -> bool:
    v = value.strip()
    if not v or len(v) < 2 or len(v) > 60:
        return False
    if not re.search(r"[A-Za-z]", v):
        return False
    # avoid misclassifying emails / numbers / long tokens as names
    if "@" in v or v.replace(" ", "").isdigit():
        return False
    return v.count(" ") <= 3


def scan_record(index: int, record: Dict[str, object]) -> RecordResult:
    """Classify a single record dict (from CSV/JSON). Field names are matched
    case-insensitively and by intent via substring."""
    res = RecordResult(index=index)
    name_found = False
    dob_found = False
    ssn_valid = False
    ssn_raw = ""
    dl_states: List[str] = []
    dl_value = ""

    def key_like(key: str, *tokens: str) -> bool:
        k = key.lower()
        return any(tok in k for tok in tokens) and len(k) < 24

    for key, raw in record.items():
        if raw is None:
            continue
        value = str(raw).strip()
        if not value:
            continue

        if key_like(key, "ssn", "social"):
            norm = normalize_ssn(value)
            if norm:
                ok, reason = validate_ssn(norm)
                if ok:
                    ssn_valid = True
                    ssn_raw = norm
                    res.add("ssn", ssn_raw, "validated SSN (area/group/serial OK)",
                            "HIGH")
                else:
                    res.add("ssn_mask", value, f"SSN-shaped but {reason}", "LOW")
            continue

        if key_like(key, "dl", "license", "drivers", "driver"):
            states = detect_dl(value)
            if states:
                dl_states = states
                dl_value = value
                sev = "MEDIUM" if states == ["generic"] else "MEDIUM"
                res.add("dl", value, "states=" + ",".join(states), sev)
            continue

        if key_like(key, "dob", "birth", "bday"):
            if detect_dob(value):
                dob_found = True
                res.add("dob", value, "date of birth", "MEDIUM")
            continue

        if key_like(key, "email", "mail"):
            if detect_email(value):
                res.add("email", value, "email address", "LOW")
            continue

        if key_like(key, "phone", "mobile", "cell", "tel"):
            if detect_phone(value):
                res.add("phone", value, "phone number", "LOW")
            continue

        if key_like(key, "name", "first", "last", "fullname", "person"):
            if _looks_like_name(value):
                name_found = True
                res.add("name", value, "personal name", "LOW")
            continue

        if key_like(key, "pass", "password", "secret"):
            res.add("password", "*redacted*", "credential/password field", "MEDIUM")
            continue

        # Loose detection: unknown field with SSN-shaped content.
        norm = normalize_ssn(value)
        if norm and not key_like(key, "acc", "id", "member", "zip", "order"):
            ok, reason = validate_ssn(norm)
            if ok:
                ssn_valid = True
                ssn_raw = norm
                res.add("ssn", ssn_raw, "validated SSN in loose field", "HIGH")

    # ---- Severity composition (confidence-weighted, honest) ----
    have_ssn = ssn_valid
    have_dl = bool(dl_states)
    if have_ssn and name_found and dob_found:
        res.severity = "CRIT"  # real Social Security number + name + DOB
    elif have_ssn and (name_found or dob_found):
        res.severity = "CRIT"
    elif have_dl and name_found and dob_found and not have_ssn:
        res.severity = "HIGH"
    elif have_ssn:
        res.severity = "HIGH"
    elif have_dl and name_found:
        res.severity = "MEDIUM"
    # else keep LOW/MEDIUM from individual findings

    if ssn_raw:
        res.present_assets.add("ssn_valid")
    return res


@dataclass
class ScanTotals:
    scanned: int
    count_by_severity: Dict[str, int] = field(default_factory=dict)
    exposed_ssns: int = 0
    exposed_dls: int = 0
    states_hit: set = field(default_factory=set)
    critical_ids: List[int] = field(default_factory=list)

    @property
    def max_severity(self) -> str:
        present = [s for s in ("CRIT", "HIGH", "MEDIUM", "LOW") if self.count_by_severity.get(s)]
        return present[0] if present else "LOW"


def aggregate(results: List[RecordResult], total_scanned: int) -> ScanTotals:
    t = ScanTotals(scanned=total_scanned)
    for r in results:
        t.count_by_severity[r.severity] = t.count_by_severity.get(r.severity, 0) + 1
        for f in r.findings:
            if f.asset == "ssn" and f.severity == "HIGH":
                t.exposed_ssns += 1
            if f.asset == "dl":
                for st in f.detail.replace("states=", "").split(","):
                    if st and st != "generic":
                        t.states_hit.add(st)
                if f.detail != "states=generic":
                    t.exposed_dls += 1
        if r.severity == "CRIT":
            t.critical_ids.append(r.index)
    return t


def exit_code(totals: ScanTotals, warn_threshold: int = 1) -> int:
    """CI gate: CRIT always fails hard; HIGH fails when threshold met."""
    if totals.count_by_severity.get("CRIT"):
        return EXIT_CRITICAL
    if totals.count_by_severity.get("HIGH", 0) >= warn_threshold:
        return EXIT_HIGH
    return EXIT_OK