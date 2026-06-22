"""Tests for PredictGuard risk scoring engine."""

from datetime import datetime, timezone, timedelta
from predictguard.models import Trade, Market, RiskLevel, Jurisdiction
from predictguard.risk import RiskScorer


def _make_trade(tid, trader, market="M001", side="buy", outcome="Yes",
                price=0.5, quantity=10, platform="kalshi",
                jurisdiction=None, timestamp=None):
    return Trade(
        tid=tid, market_id=market, trader_id=trader,
        side=side, outcome=outcome, price=price, quantity=quantity,
        platform=platform, jurisdiction=jurisdiction,
        timestamp=timestamp or datetime.now(timezone.utc),
    )


class TestRiskScorerEmpty:
    def test_no_trades(self):
        scorer = RiskScorer()
        result = scorer.score_trader("unknown")
        assert result.risk_level == RiskLevel.LOW
        assert result.risk_score == 0.0

    def test_no_trades_market(self):
        scorer = RiskScorer()
        result = scorer.score_market("unknown")
        assert result.risk_level == RiskLevel.LOW
        assert result.risk_score == 0.0


class TestWashTrading:
    def test_wash_trading_detected(self):
        scorer = RiskScorer()
        now = datetime.now(timezone.utc)
        trades = [
            _make_trade("T1", "alice", side="buy", outcome="Yes"),
            _make_trade("T2", "alice", side="sell", outcome="Yes"),
        ]
        scorer.add_trades(trades)
        result = scorer.score_trader("alice")
        assert result.risk_score >= 0.75
        assert any("Wash" in f for f in result.flags)

    def test_no_wash_trading(self):
        scorer = RiskScorer()
        trades = [
            _make_trade("T1", "alice", side="buy", outcome="Yes"),
            _make_trade("T2", "alice", side="buy", outcome="No"),
        ]
        scorer.add_trades(trades)
        result = scorer.score_trader("alice")
        assert result.risk_score < 0.5


class TestVolumeAnomaly:
    def test_high_volume(self):
        scorer = RiskScorer()
        # price=0.5 * quantity=200_000 = $100,000+ total volume
        trades = [
            _make_trade("T1", "alice", price=0.5, quantity=200_000),
        ]
        scorer.add_trades(trades)
        result = scorer.score_trader("alice")
        assert result.risk_score > 0.0

    def test_normal_volume(self):
        scorer = RiskScorer()
        trades = [
            _make_trade("T1", "alice", price=0.5, quantity=10),
        ]
        scorer.add_trades(trades)
        result = scorer.score_trader("alice")
        assert result.risk_score < 0.4


class TestConcentration:
    def test_concentrated_trading(self):
        scorer = RiskScorer()
        now = datetime.now(timezone.utc)
        trades = [
            _make_trade(f"T{i}", "alice", market="M001", side="buy", outcome="Yes")
            for i in range(10)
        ]
        # Add 1 trade in a different market
        trades.append(_make_trade("T10", "alice", market="M002", side="buy", outcome="Yes"))
        scorer.add_trades(trades)
        result = scorer.score_trader("alice")
        assert result.risk_score > 0.0

    def test_diversified_trading(self):
        scorer = RiskScorer()
        base = datetime(2026, 6, 22, 12, 0, 0, tzinfo=timezone.utc)
        trades = [
            _make_trade(f"T{i}", "alice", market=f"M{i:03d}", side="buy", outcome="Yes",
                       timestamp=base + timedelta(minutes=i * 30))
            for i in range(10)
        ]
        scorer.add_trades(trades)
        result = scorer.score_trader("alice")
        assert result.risk_score < 0.5


class TestRapidTrading:
    def test_rapid_trading_detected(self):
        scorer = RiskScorer()
        base = datetime(2026, 6, 22, 12, 0, 0, tzinfo=timezone.utc)
        trades = [
            _make_trade(f"T{i}", "alice", timestamp=base + timedelta(seconds=i * 10))
            for i in range(15)
        ]
        scorer.add_trades(trades)
        result = scorer.score_trader("alice")
        assert result.risk_score >= 0.5
        assert any("Rapid" in f for f in result.flags)

    def test_normal_paced_trading(self):
        scorer = RiskScorer()
        base = datetime(2026, 6, 22, 12, 0, 0, tzinfo=timezone.utc)
        trades = [
            _make_trade(f"T{i}", "alice", market=f"M{i:03d}", side="buy", outcome="Yes",
                       timestamp=base + timedelta(minutes=i * 30))
            for i in range(5)
        ]
        scorer.add_trades(trades)
        result = scorer.score_trader("alice")
        assert result.risk_score < 0.5


class TestRestrictedJurisdiction:
    def test_nevada_trade_flagged(self):
        scorer = RiskScorer()
        trades = [
            _make_trade("T1", "eve", jurisdiction=Jurisdiction.NEVADA, price=0.8, quantity=100),
        ]
        scorer.add_trades(trades)
        result = scorer.score_trader("eve")
        assert result.risk_score >= 0.7
        assert any("restricted" in f.lower() for f in result.flags)

    def test_texas_trade_not_flagged(self):
        scorer = RiskScorer()
        trades = [
            _make_trade("T1", "bob", jurisdiction=Jurisdiction.TEXAS, price=0.5, quantity=10),
        ]
        scorer.add_trades(trades)
        result = scorer.score_trader("bob")
        assert result.risk_score < 0.5


class TestScoreAllTraders:
    def test_scores_all(self):
        scorer = RiskScorer()
        trades = [
            _make_trade("T1", "alice", side="buy", outcome="Yes"),
            _make_trade("T2", "alice", side="sell", outcome="Yes"),
            _make_trade("T3", "bob", side="buy", outcome="No"),
        ]
        scorer.add_trades(trades)
        results = scorer.score_all_traders()
        assert len(results) == 2
        # Alice should be higher risk (wash trading)
        assert results[0].target_id == "alice"
        assert results[0].risk_score > results[1].risk_score


class TestScoreAllMarkets:
    def test_scores_markets(self):
        scorer = RiskScorer()
        trades = [
            _make_trade("T1", "a1", market="M001", side="buy", outcome="Yes", price=0.5, quantity=100),
            _make_trade("T2", "a2", market="M001", side="buy", outcome="Yes", price=0.5, quantity=100),
            _make_trade("T3", "a3", market="M001", side="buy", outcome="Yes", price=0.5, quantity=100),
        ]
        scorer.add_trades(trades)
        results = scorer.score_all_markets()
        assert len(results) >= 1


class TestMarketRisk:
    def test_one_sided_trading(self):
        scorer = RiskScorer()
        trades = [
            _make_trade(f"T{i}", f"trader_{i}", market="M001", side="buy", outcome="Yes")
            for i in range(10)
        ]
        scorer.add_trades(trades)
        result = scorer.score_market("M001")
        assert result.risk_score > 0.0
        assert any("One-sided" in f for f in result.flags)

    def test_low_trader_high_volume(self):
        scorer = RiskScorer()
        trades = [
            _make_trade("T1", "a1", market="M001", side="buy", outcome="Yes", price=0.9, quantity=10000),
            _make_trade("T2", "a2", market="M001", side="sell", outcome="Yes", price=0.1, quantity=10000),
        ]
        scorer.add_trades(trades)
        result = scorer.score_market("M001")
        assert result.risk_score > 0.0
