"""Tests for PredictGuard models."""

from datetime import datetime, timezone
from predictguard.models import (
    Trade,
    Market,
    ComplianceReport,
    RiskAssessment,
    AuditEntry,
    RegulatoryStatus,
    Jurisdiction,
    RiskLevel,
)


class TestJurisdiction:
    def test_us_state_codes(self):
        assert Jurisdiction.CALIFORNIA.value == "CA"
        assert Jurisdiction.NEW_YORK.value == "NY"
        assert Jurisdiction.TEXAS.value == "TX"

    def test_international_codes(self):
        assert Jurisdiction.UNITED_KINGDOM.value == "UK"
        assert Jurisdiction.EUROPEAN_UNION.value == "EU"

    def test_from_value(self):
        j = Jurisdiction("CA")
        assert j == Jurisdiction.CALIFORNIA


class TestRiskLevel:
    def test_values(self):
        assert RiskLevel.LOW.value == "LOW"
        assert RiskLevel.CRITICAL.value == "CRITICAL"


class TestTrade:
    def test_create_trade(self):
        t = Trade(
            tid="T001",
            market_id="M001",
            trader_id="alice",
            side="buy",
            outcome="Yes",
            price=0.62,
            quantity=100,
        )
        assert t.tid == "T001"
        assert t.side == "buy"
        assert t.price == 0.62
        assert t.quantity == 100
        assert t.platform == ""
        assert t.jurisdiction is None

    def test_trade_with_jurisdiction(self):
        t = Trade(
            tid="T002",
            market_id="M001",
            trader_id="bob",
            side="sell",
            outcome="No",
            price=0.38,
            quantity=50,
            platform="kalshi",
            jurisdiction=Jurisdiction.CALIFORNIA,
        )
        assert t.jurisdiction == Jurisdiction.CALIFORNIA
        assert t.platform == "kalshi"

    def test_trade_timestamp_auto(self):
        t = Trade(tid="T003", market_id="M001", trader_id="alice", side="buy",
                  outcome="Yes", price=0.5, quantity=10)
        assert t.timestamp is not None


class TestMarket:
    def test_create_market(self):
        m = Market(mid="M001", question="Will Trump win 2028?", category="politics")
        assert m.mid == "M001"
        assert m.resolved is False
        assert m.outcome is None

    def test_market_with_prices(self):
        m = Market(
            mid="M002",
            question="BTC > $100k by Dec 2026?",
            category="crypto",
            outcome_prices={"Yes": 0.45, "No": 0.55},
            volume_24h=1_500_000,
        )
        assert m.outcome_prices["Yes"] == 0.45
        assert m.volume_24h == 1_500_000


class TestComplianceReport:
    def test_create_report(self):
        now = datetime.now(timezone.utc)
        r = ComplianceReport(
            rid="RPT-000001",
            generated_at=now,
            period_start=now,
            period_end=now,
            jurisdiction=Jurisdiction.CALIFORNIA,
            total_trades=100,
            total_volume=50000.0,
        )
        assert r.rid == "RPT-000001"
        assert r.compliance_score == 1.0
        assert r.flagged_trades == 0


class TestRiskAssessment:
    def test_create_assessment(self):
        a = RiskAssessment(
            target_id="trader_alice",
            target_type="trader",
            risk_level=RiskLevel.HIGH,
            risk_score=0.85,
            flags=["Wash trading detected"],
        )
        assert a.risk_level == RiskLevel.HIGH
        assert a.risk_score == 0.85
        assert len(a.flags) == 1


class TestAuditEntry:
    def test_create_entry(self):
        e = AuditEntry(
            eid="AUD-000001",
            event_type="trade",
            actor="alice",
            description="Buy Yes @ 0.62",
        )
        assert e.eid == "AUD-000001"
        assert e.data_hash == ""
