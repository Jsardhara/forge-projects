"""Alert engine — generate structured alerts from price deltas."""

from __future__ import annotations

from datetime import datetime, timezone

from .models import (
    AlertSeverity,
    ChangeDirection,
    PriceAlert,
    PriceDelta,
    Provider,
)


def _severity_for_pct(pct: float) -> AlertSeverity:
    """Classify alert severity based on percentage magnitude."""
    abs_pct = abs(pct)
    if abs_pct >= 50.0:
        return AlertSeverity.CRITICAL
    if abs_pct >= 25.0:
        return AlertSeverity.HIGH
    if abs_pct >= 10.0:
        return AlertSeverity.MEDIUM
    return AlertSeverity.LOW


def generate_alerts(deltas: list[PriceDelta]) -> list[PriceAlert]:
    """Generate structured alerts from detected price changes."""
    alerts: list[PriceAlert] = []
    now = datetime.now(timezone.utc)

    for delta in deltas:
        if delta.direction == ChangeDirection.NO_CHANGE:
            continue

        if delta.direction == ChangeDirection.NEW_MODEL:
            alerts.append(
                PriceAlert(
                    provider=delta.provider,
                    model_id=delta.model_id,
                    severity=AlertSeverity.INFO,
                    direction=ChangeDirection.NEW_MODEL,
                    message=f"New model listed: {delta.provider.value}/{delta.model_id}",
                    detail=(
                        f"Input: ${delta.new_input:.2f}/Mtok, "
                        f"Output: ${delta.new_output:.2f}/Mtok"
                    ),
                    max_pct=0.0,
                    detected_at=now,
                )
            )
            continue

        max_pct = delta.max_pct
        severity = _severity_for_pct(max_pct)

        if delta.direction == ChangeDirection.PRICE_DROP:
            msg = f"Price drop: {delta.provider.value}/{delta.model_id} "
            msg += f"({max_pct:.1f}% reduction)"
            detail = (
                f"Input: ${delta.old_input:.2f} → ${delta.new_input:.2f}/Mtok "
                f"({delta.input_pct:+.1f}%), "
                f"Output: ${delta.old_output:.2f} → ${delta.new_output:.2f}/Mtok "
                f"({delta.output_pct:+.1f}%)"
            )
        else:
            msg = f"Price increase: {delta.provider.value}/{delta.model_id} "
            msg += f"({max_pct:.1f}% hike)"
            detail = (
                f"Input: ${delta.old_input:.2f} → ${delta.new_input:.2f}/Mtok "
                f"({delta.input_pct:+.1f}%), "
                f"Output: ${delta.old_output:.2f} → ${delta.new_output:.2f}/Mtok "
                f"({delta.output_pct:+.1f}%)"
            )

        alerts.append(
            PriceAlert(
                provider=delta.provider,
                model_id=delta.model_id,
                severity=severity,
                direction=delta.direction,
                message=msg,
                detail=detail,
                max_pct=max_pct,
                detected_at=now,
            )
        )

    return alerts


def generate_price_war_alert(
    war_deltas: list[PriceDelta],
) -> PriceAlert:
    """Generate a single alert for a detected price war."""
    providers = sorted(set(d.provider.value for d in war_deltas))
    models = sorted(set(d.model_id for d in war_deltas))
    max_pct = max(d.max_pct for d in war_deltas)

    return PriceAlert(
        provider=Provider(providers[0]),  # representative provider
        model_id=",".join(models[:3]),
        severity=AlertSeverity.CRITICAL,
        direction=ChangeDirection.PRICE_DROP,
        message=f"PRICE WAR detected: {len(providers)} providers dropped prices simultaneously",
        detail=(
            f"Providers: {', '.join(providers)} | "
            f"Models: {', '.join(models)} | "
            f"Max reduction: {max_pct:.1f}%"
        ),
        max_pct=max_pct,
        detected_at=datetime.now(timezone.utc),
    )
