"""Estimated-vs-actual reconciliation engine for costrecon."""

from typing import Dict, List

from .models import Estimate, ReconciliationReport, Variance

# Classification constants
WITHIN_TOLERANCE = "WITHIN_TOLERANCE"
OVER_ESTIMATE = "OVER_ESTIMATE"
UNDER_ESTIMATE = "UNDER_ESTIMATE"
UNESTIMATED = "UNESTIMATED"
NO_ACTUAL = "NO_ACTUAL"


class Reconciler:
    def __init__(self, threshold_pct: float = 5.0):
        # Tolerance band: |pct| <= threshold_pct is considered "within estimate".
        self.threshold_pct = float(threshold_pct)

    def reconcile(
        self,
        actuals_by_key: Dict[str, float],
        estimates: List[Estimate],
    ) -> ReconciliationReport:
        estimate_map = {e.key: e.estimated_cost for e in estimates}
        variances: List[Variance] = []
        unestimated: List[str] = []

        for key, estimated in estimate_map.items():
            actual = actuals_by_key.get(key, 0.0)
            variances.append(self._variance(key, estimated, actual))

        # Services present in actuals but never estimated -> unexpected spend.
        for key in actuals_by_key:
            if key not in estimate_map:
                unestimated.append(key)
                variances.append(self._variance(key, 0.0, actuals_by_key[key]))

        anomalies = [v for v in variances if v.anomaly]
        total_estimated = sum(estimate_map.values())
        total_actual = sum(actuals_by_key.values())

        # Sort: anomalies first, then by absolute delta descending.
        variances.sort(key=lambda v: (not v.anomaly, -abs(v.delta)))

        return ReconciliationReport(
            by_key=variances,
            total_estimated=round(total_estimated, 4),
            total_actual=round(total_actual, 4),
            anomalies=anomalies,
            unestimated_services=unestimated,
        )

    def _variance(self, key: str, estimated: float, actual: float) -> Variance:
        delta = round(actual - estimated, 4)
        if estimated == 0 and actual == 0:
            classification = NO_ACTUAL
            anomaly = False
            pct = None
        elif estimated == 0 and actual > 0:
            classification = UNESTIMATED
            anomaly = True
            pct = None
        elif actual == 0 and estimated > 0:
            # Budgeted for a resource that saw no actual spend this period.
            classification = NO_ACTUAL
            anomaly = False
            pct = None
        else:
            pct = round(delta / estimated * 100.0, 2)
            if abs(pct) <= self.threshold_pct:
                classification = WITHIN_TOLERANCE
                anomaly = False
            elif delta > 0:
                classification = OVER_ESTIMATE
                anomaly = True
            else:
                classification = UNDER_ESTIMATE
                anomaly = True
        return Variance(
            key=key,
            estimated=round(estimated, 4),
            actual=round(actual, 4),
            delta=delta,
            pct=pct,
            classification=classification,
            anomaly=anomaly,
        )
