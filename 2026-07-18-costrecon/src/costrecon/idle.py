"""Idle / over-provisioned resource detection for costrecon.

Reads a utilization CSV (one row per billable resource) and flags resources
that are costing money but delivering little value:

* compute resources (ec2/rds) with utilization below ``idle_threshold_pct``
* unattached EBS volumes (state == "unattached")
* unassociated Elastic IPs (state == "available"/"unassociated")
* snapshots older than ``snapshot_max_age_days``

Estimated savings are computed conservatively so the report never over-promises.
"""

from datetime import datetime, timezone as tz
from typing import List, Optional

from .models import IdleFinding, IdleReport, ResourceUtilization

# Severity thresholds (share of capacity wasted)
SEV_WARN = 0.50      # >50% wasted -> WARN
SEV_CRITICAL = 0.80  # >80% wasted -> CRITICAL


class IdleDetector:
    def __init__(
        self,
        idle_threshold_pct: float = 5.0,
        snapshot_max_age_days: float = 30.0,
        min_cost: float = 0.01,
    ):
        self.idle_threshold_pct = float(idle_threshold_pct)
        self.snapshot_max_age_days = float(snapshot_max_age_days)
        self.min_cost = float(min_cost)

    def detect(
        self,
        rows: List[ResourceUtilization],
        as_of: Optional[datetime] = None,
    ) -> IdleReport:
        if as_of is None:
            as_of = datetime.now(tz.utc)
        findings: List[IdleFinding] = []
        total_cost = 0.0

        for r in rows:
            total_cost += r.monthly_cost
            if r.monthly_cost < self.min_cost:
                continue

            # 1) Utilization-based (compute resources)
            if r.utilization_pct is not None:
                if r.utilization_pct < self.idle_threshold_pct:
                    wasted = (100.0 - r.utilization_pct) / 100.0
                    savings = round(r.monthly_cost * wasted, 4)
                    findings.append(
                        self._finding(
                            r,
                            reason=f"utilization {r.utilization_pct:.1f}% < {self.idle_threshold_pct:.1f}% threshold",
                            wasted=wasted,
                            savings=savings,
                        )
                    )
                continue

            # 2) State-based (non-utilization resources)
            state = (r.state or "").strip().lower()
            if r.rtype == "ebs" and state in ("unattached", "available", "unused"):
                findings.append(
                    self._finding(r, reason="EBS volume unattached", wasted=1.0,
                                  savings=round(r.monthly_cost, 4))
                )
            elif r.rtype == "eip" and state in ("available", "unassociated", "unattached"):
                findings.append(
                    self._finding(r, reason="Elastic IP not associated", wasted=1.0,
                                  savings=round(r.monthly_cost, 4))
                )
            elif r.rtype == "snapshot":
                age = r.age_days
                if age is None:
                    # No age supplied -> cannot judge staleness; skip silently.
                    continue
                if age > self.snapshot_max_age_days:
                    wasted = min(1.0, (age - self.snapshot_max_age_days) / max(age, 1.0))
                    findings.append(
                        self._finding(
                            r,
                            reason=f"snapshot age {age:.0f}d > {self.snapshot_max_age_days:.0f}d",
                            wasted=wasted,
                            savings=round(r.monthly_cost * wasted, 4),
                        )
                    )

        findings.sort(key=lambda f: -f.estimated_savings)
        return IdleReport(
            findings=findings,
            total_savings=round(sum(f.estimated_savings for f in findings), 4),
            total_cost=round(total_cost, 4),
        )

    def _finding(self, r, reason, wasted, savings) -> IdleFinding:
        if wasted >= SEV_CRITICAL:
            severity = "CRITICAL"
        elif wasted >= SEV_WARN:
            severity = "WARN"
        else:
            severity = "INFO"
        return IdleFinding(
            resource_id=r.resource_id,
            rtype=r.rtype,
            reason=reason,
            severity=severity,
            monthly_cost=round(r.monthly_cost, 4),
            estimated_savings=savings,
        )
