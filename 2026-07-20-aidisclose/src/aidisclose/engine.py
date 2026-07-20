"""Applicability + gap-scoring engine for aidisclose."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timezone
from typing import List, Optional, Tuple

from .models import (
    Mandate, MandateStatus, Obligation, OrgProfile, SEVERITY_WEIGHT,
)

# Risk bands, evaluated high-threshold-first.
_RISK_BANDS = [
    (80.0, "CRITICAL"),
    (50.0, "HIGH"),
    (20.0, "MEDIUM"),
    (0.0, "LOW"),
]


def _band(score: float) -> str:
    for threshold, band in _RISK_BANDS:
        if score >= threshold:
            return band
    return "LOW"


def _is_enforceable(m: Mandate, ref: date) -> bool:
    """A mandate is enforceable (scores into the gap) when it is IN_FORCE and
    its effective date has arrived (or it has no effective date)."""
    if m.status != MandateStatus.IN_FORCE:
        return False
    if m.effective_date is not None and m.effective_date > ref:
        return False
    return True


def mandate_applies(profile: OrgProfile, m: Mandate) -> bool:
    """True if the org's profile triggers this mandate's scope."""
    if m.jurisdiction not in profile.jurisdictions_set():
        return False
    if not m.sector_applies(profile.sectors_set()):
        return False
    if not m.use_applies(profile.uses_set()):
        return False
    return True


@dataclass
class ApplicableMandate:
    mandate: Mandate
    met: Tuple[Obligation, ...]
    unmet: Tuple[Obligation, ...]
    gap_weight: int
    total_weight: int

    @property
    def ratio(self) -> float:
        if self.total_weight == 0:
            return 0.0
        return self.gap_weight / self.total_weight


@dataclass
class ComplianceReport:
    profile_name: str
    reference_date: date
    applicable: Tuple[ApplicableMandate, ...]
    monitored: Tuple[Mandate, ...]
    score: float
    band: str
    blocking: bool

    @property
    def applicable_count(self) -> int:
        return len(self.applicable)

    @property
    def monitored_count(self) -> int:
        return len(self.monitored)

    def to_dict(self) -> dict:
        return {
            "profile": self.profile_name,
            "reference_date": self.reference_date.isoformat(),
            "score": round(self.score, 2),
            "band": self.band,
            "blocking": self.blocking,
            "applicable_count": len(self.applicable),
            "monitored_count": len(self.monitored),
            "applicable": [
                {
                    "mid": am.mandate.mid,
                    "jurisdiction": am.mandate.jurisdiction,
                    "title": am.mandate.title,
                    "status": am.mandate.status.value,
                    "gap_weight": am.gap_weight,
                    "total_weight": am.total_weight,
                    "ratio": round(am.ratio, 4),
                    "met": [o.code for o in am.met],
                    "unmet": [
                        {"code": o.code, "severity": o.severity.value}
                        for o in am.unmet
                    ],
                }
                for am in self.applicable
            ],
            "monitored": [
                {"mid": m.mid, "jurisdiction": m.jurisdiction,
                 "title": m.title, "status": m.status.value}
                for m in self.monitored
            ],
        }


def analyze(
    profile: OrgProfile,
    mandates: Optional[Tuple[Mandate, ...]] = None,
) -> ComplianceReport:
    """Compute applicable mandates, gaps, score, and risk band for a profile."""
    if mandates is None:
        from .rules import load_mandates
        mandates = load_mandates()

    ref = profile.reference_date or date.today()

    applicable: List[ApplicableMandate] = []
    monitored: List[Mandate] = []
    implemented = profile.implemented_set()

    for m in mandates:
        if not mandate_applies(profile, m):
            continue
        if _is_enforceable(m, ref):
            met = tuple(o for o in m.obligations if o.code in implemented)
            unmet = tuple(o for o in m.obligations if o.code not in implemented)
            gap_w = sum(o.weight for o in unmet)
            total_w = sum(o.weight for o in m.obligations)
            applicable.append(ApplicableMandate(
                mandate=m, met=met, unmet=unmet,
                gap_weight=gap_w, total_weight=total_w))
        else:
            # upcoming / proposed -> watch only, never scored
            monitored.append(m)

    total_gap = sum(am.gap_weight for am in applicable)
    total_possible = sum(am.total_weight for am in applicable)
    score = 0.0
    if total_possible > 0:
        score = 100.0 * total_gap / total_possible

    blocking = any(
        o.severity.value == "critical" for am in applicable for o in am.unmet
    )

    return ComplianceReport(
        profile_name=profile.name,
        reference_date=ref,
        applicable=tuple(applicable),
        monitored=tuple(monitored),
        score=round(score, 2),
        band=_band(score),
        blocking=blocking,
    )
