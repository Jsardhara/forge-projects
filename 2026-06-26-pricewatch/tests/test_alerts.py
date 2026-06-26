"""Tests for PriceWatch alert engine."""

import pytest
from datetime import datetime, timezone

from pricewatch.models import (
    AlertSeverity,
    ChangeDirection,
    PriceDelta,
    Provider,
)
from pricewatch.alerts import generate_alerts, generate_price_war_alert


def _make_delta(
    provider: Provider = Provider.OPENAI,
    model_id: str = "gpt-4o",
    direction: ChangeDirection = ChangeDirection.PRICE_DROP,
    input_pct: float = -20.0,
    output_pct: float = -20.0,
    old_input: float = 2.50,
    old_output: float = 10.00,
    new_input: float = 2.00,
    new_output: float = 8.00,
) -> PriceDelta:
    return PriceDelta(
        provider=provider,
        model_id=model_id,
        direction=direction,
        input_delta=new_input - old_input,
        output_delta=new_output - old_output,
        input_pct=input_pct,
        output_pct=output_pct,
        old_input=old_input,
        old_output=old_output,
        new_input=new_input,
        new_output=new_output,
    )


class TestGenerateAlerts:
    """Tests for generate_alerts function."""

    def test_price_drop_alert(self):
        delta = _make_delta(direction=ChangeDirection.PRICE_DROP, input_pct=-20.0, output_pct=-20.0)
        alerts = generate_alerts([delta])
        assert len(alerts) == 1
        assert alerts[0].severity == AlertSeverity.MEDIUM
        assert alerts[0].direction == ChangeDirection.PRICE_DROP
        assert "Price drop" in alerts[0].message

    def test_large_drop_critical_severity(self):
        delta = _make_delta(
            direction=ChangeDirection.PRICE_DROP,
            input_pct=-55.0, output_pct=-55.0,
            old_input=2.50, old_output=10.00,
            new_input=1.125, new_output=4.50,
        )
        alerts = generate_alerts([delta])
        assert alerts[0].severity == AlertSeverity.CRITICAL

    def test_small_drop_low_severity(self):
        delta = _make_delta(
            direction=ChangeDirection.PRICE_DROP,
            input_pct=-5.0, output_pct=-5.0,
            old_input=2.50, old_output=10.00,
            new_input=2.375, new_output=9.50,
        )
        alerts = generate_alerts([delta])
        assert alerts[0].severity == AlertSeverity.LOW

    def test_price_increase_alert(self):
        delta = _make_delta(
            direction=ChangeDirection.PRICE_INCREASE,
            input_pct=25.0, output_pct=25.0,
            old_input=2.50, old_output=10.00,
            new_input=3.125, new_output=12.50,
        )
        alerts = generate_alerts([delta])
        assert len(alerts) == 1
        assert alerts[0].direction == ChangeDirection.PRICE_INCREASE
        assert "Price increase" in alerts[0].message
        assert alerts[0].severity == AlertSeverity.HIGH

    def test_new_model_alert(self):
        delta = _make_delta(
            direction=ChangeDirection.NEW_MODEL,
            old_input=0.0, old_output=0.0,
            new_input=1.00, new_output=4.00,
        )
        alerts = generate_alerts([delta])
        assert len(alerts) == 1
        assert alerts[0].severity == AlertSeverity.INFO
        assert "New model" in alerts[0].message

    def test_no_change_ignored(self):
        delta = _make_delta(direction=ChangeDirection.NO_CHANGE)
        alerts = generate_alerts([delta])
        assert len(alerts) == 0

    def test_multiple_alerts_sorted(self):
        deltas = [
            _make_delta(model_id="cheap", direction=ChangeDirection.PRICE_DROP, input_pct=-5.0, output_pct=-5.0, new_input=2.375, new_output=9.50),
            _make_delta(model_id="expensive", direction=ChangeDirection.PRICE_INCREASE, input_pct=30.0, output_pct=30.0, new_input=3.25, new_output=13.00),
        ]
        alerts = generate_alerts(deltas)
        assert len(alerts) == 2


class TestGeneratePriceWarAlert:
    """Tests for price war alert generation."""

    def test_price_war_alert(self):
        deltas = [
            _make_delta(provider=Provider.OPENAI, model_id="gpt-4o", direction=ChangeDirection.PRICE_DROP, input_pct=-25.0, output_pct=-25.0, new_input=1.875, new_output=7.50),
            _make_delta(provider=Provider.ANTHROPIC, model_id="claude-sonnet-4", direction=ChangeDirection.PRICE_DROP, input_pct=-30.0, output_pct=-30.0, old_input=3.0, old_output=15.0, new_input=2.10, new_output=10.50),
        ]
        alert = generate_price_war_alert(deltas)
        assert alert.severity == AlertSeverity.CRITICAL
        assert "PRICE WAR" in alert.message
        assert alert.direction == ChangeDirection.PRICE_DROP
