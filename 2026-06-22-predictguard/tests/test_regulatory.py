"""Tests for PredictGuard regulatory tracker."""

import pytest
from predictguard.models import Jurisdiction, RegulatoryStatus
from predictguard.regulatory import RegulatoryTracker


class TestRegulatoryTrackerInit:
    def test_loads_defaults(self):
        tracker = RegulatoryTracker()
        all_regs = tracker.get_all()
        assert len(all_regs) > 0

    def test_has_key_jurisdictions(self):
        tracker = RegulatoryTracker()
        assert tracker.get_status(Jurisdiction.CALIFORNIA) is not None
        assert tracker.get_status(Jurisdiction.NEVADA) is not None
        assert tracker.get_status(Jurisdiction.NEW_YORK) is not None
        assert tracker.get_status(Jurisdiction.TEXAS) is not None
        assert tracker.get_status(Jurisdiction.UNITED_KINGDOM) is not None


class TestRegulatoryStatus:
    def test_allowed_state(self):
        tracker = RegulatoryTracker()
        ca = tracker.get_status(Jurisdiction.CALIFORNIA)
        assert ca is not None
        assert ca.status == "ALLOWED"
        assert ca.cftc_compliant is True

    def test_restricted_state(self):
        tracker = RegulatoryTracker()
        nv = tracker.get_status(Jurisdiction.NEVADA)
        assert nv is not None
        assert nv.status == "CEASE_AND_DESIST"

    def test_uk_restricted(self):
        tracker = RegulatoryTracker()
        uk = tracker.get_status(Jurisdiction.UNITED_KINGDOM)
        assert uk is not None
        assert uk.status == "RESTRICTED"

    def test_eu_unclear(self):
        tracker = RegulatoryTracker()
        eu = tracker.get_status(Jurisdiction.EUROPEAN_UNION)
        assert eu is not None
        assert eu.status == "UNCLEAR"


class TestIsTradeAllowed:
    def test_allowed_in_california(self):
        tracker = RegulatoryTracker()
        allowed, reason = tracker.is_trade_allowed(Jurisdiction.CALIFORNIA)
        assert allowed is True
        assert "Allowed" in reason

    def test_blocked_in_nevada(self):
        tracker = RegulatoryTracker()
        allowed, reason = tracker.is_trade_allowed(Jurisdiction.NEVADA)
        assert allowed is False
        assert "CEASE_AND_DESIST" in reason

    def test_blocked_in_new_york(self):
        tracker = RegulatoryTracker()
        allowed, reason = tracker.is_trade_allowed(Jurisdiction.NEW_YORK)
        assert allowed is False

    def test_unknown_jurisdiction(self):
        tracker = RegulatoryTracker()
        # Create a jurisdiction not in the tracker
        allowed, reason = tracker.is_trade_allowed(Jurisdiction.WYOMING)
        assert allowed is False
        assert "Unknown" in reason or "default deny" in reason


class TestGetByStatus:
    def test_get_restricted(self):
        tracker = RegulatoryTracker()
        restricted = tracker.get_restricted()
        assert len(restricted) > 0
        for r in restricted:
            assert r.status in ("CEASE_AND_DESIST", "BAN_PROPOSED", "RESTRICTED")

    def test_get_by_status_allowed(self):
        tracker = RegulatoryTracker()
        allowed = tracker.get_by_status("ALLOWED")
        assert len(allowed) > 0
        for a in allowed:
            assert a.status == "ALLOWED"


class TestComplianceCheck:
    def test_compliant_trades(self):
        from predictguard.models import Trade
        tracker = RegulatoryTracker()
        trades = [
            Trade(tid="T1", market_id="M1", trader_id="alice", side="buy",
                  outcome="Yes", price=0.5, quantity=10,
                  jurisdiction=Jurisdiction.CALIFORNIA, platform="kalshi"),
        ]
        findings = tracker.compliance_check(trades)
        assert len(findings) == 0

    def test_non_compliant_trades(self):
        from predictguard.models import Trade
        tracker = RegulatoryTracker()
        trades = [
            Trade(tid="T1", market_id="M1", trader_id="eve", side="buy",
                  outcome="Yes", price=0.8, quantity=100,
                  jurisdiction=Jurisdiction.NEVADA, platform="polymarket"),
        ]
        findings = tracker.compliance_check(trades)
        assert len(findings) > 0
        assert "NOT ALLOWED" in findings[0]


class TestSummary:
    def test_summary_counts(self):
        tracker = RegulatoryTracker()
        summary = tracker.summary()
        assert "ALLOWED" in summary
        total = sum(summary.values())
        assert total > 0


class TestUpdateStatus:
    def test_update_status(self):
        tracker = RegulatoryTracker()
        new_status = RegulatoryStatus(
            jurisdiction=Jurisdiction.WYOMING,
            status="ALLOWED",
            notes="Test update",
            cftc_compliant=True,
        )
        tracker.update_status(new_status)
        result = tracker.get_status(Jurisdiction.WYOMING)
        assert result is not None
        assert result.status == "ALLOWED"
        assert result.cftc_compliant is True
