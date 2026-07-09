"""Alerting: converts exposure scores into actionable alerts.

An alert fires when an identity's exposure severity meets or exceeds a
configurable threshold, or when identity documents (SSN/passport) are
exposed regardless of count.
"""

from __future__ import annotations

from breach_sentinel.models import (
    Alert,
    ExposureScore,
    Identity,
    Severity,
)
from breach_sentinel.scorer import score_exposure


DEFAULT_THRESHOLD = Severity.MEDIUM


def build_alerts(identity: Identity, records) -> list[Alert]:
    score: ExposureScore = score_exposure(identity.iid, records)
    alerts: list[Alert] = []

    doc_exposed = bool(score.critical_types)
    above_threshold = score.severity.rank >= DEFAULT_THRESHOLD.rank

    if doc_exposed or above_threshold:
        if doc_exposed and not above_threshold:
            sev = Severity.HIGH  # identity docs are always serious
            title = f"Identity document exposure: {identity.label}"
            body = (
                f"{len(score.critical_types)} identity-document type(s) exposed "
                f"({', '.join(t.value for t in score.critical_types)}). "
                f"Treat as a credential compromise; freeze/rotate affected accounts."
            )
        else:
            sev = score.severity
            title = f"Breach exposure {sev.value.upper()}: {identity.label}"
            body = (
                f"Exposure score {score.score}/100 from {score.record_count} breach "
                f"record(s). {('Identity documents exposed: ' + ', '.join(t.value for t in score.critical_types)) if score.critical_types else 'No identity documents exposed.'}"
            )
        aid = Alert.make_aid(identity.iid, title)
        alerts.append(Alert(aid=aid, iid=identity.iid, severity=sev, title=title, body=body))

    return alerts
