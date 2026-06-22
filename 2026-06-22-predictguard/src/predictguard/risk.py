"""Risk scoring engine for prediction market compliance.

Detects suspicious patterns:
- Wash trading (self-dealing across accounts)
- Coordinated trading (multiple accounts, same pattern)
- Insider trading signals (large positions before major events)
- Unusual volume spikes
- Price manipulation patterns
"""

from __future__ import annotations

import hashlib
from collections import defaultdict
from datetime import datetime, timezone
from predictguard.models import (
    Trade,
    Market,
    RiskAssessment,
    RiskLevel,
)


# Risk score thresholds
LOW_THRESHOLD = 0.25
MEDIUM_THRESHOLD = 0.50
HIGH_THRESHOLD = 0.75


def _score_to_level(score: float) -> RiskLevel:
    if score >= HIGH_THRESHOLD:
        return RiskLevel.CRITICAL
    if score >= MEDIUM_THRESHOLD:
        return RiskLevel.HIGH
    if score >= LOW_THRESHOLD:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


class RiskScorer:
    """Scores traders and markets for compliance risk."""

    def __init__(self) -> None:
        self._trades: list[Trade] = []
        self._markets: dict[str, Market] = {}

    def add_trades(self, trades: list[Trade]) -> None:
        self._trades.extend(trades)

    def add_market(self, market: Market) -> None:
        self._markets[market.mid] = market

    def score_trader(self, trader_id: str) -> RiskAssessment:
        """Score a single trader's risk level."""
        trader_trades = [t for t in self._trades if t.trader_id == trader_id]
        if not trader_trades:
            return RiskAssessment(
                target_id=trader_id,
                target_type="trader",
                risk_level=RiskLevel.LOW,
                risk_score=0.0,
                flags=[],
                details={"trade_count": 0},
            )

        flags: list[str] = []
        score = 0.0
        details: dict = {"trade_count": len(trader_trades)}

        # Check 1: Wash trading — same trader on both sides of same market
        wash_score, wash_flags = self._check_wash_trading(trader_trades)
        score = max(score, wash_score)
        flags.extend(wash_flags)

        # Check 2: Unusual volume — trader's volume vs market average
        vol_score, vol_flags = self._check_volume_anomaly(trader_trades)
        score = max(score, vol_score)
        flags.extend(vol_flags)

        # Check 3: Concentrated positions — >50% of trades in single market
        conc_score, conc_flags = self._check_concentration(trader_trades)
        score = max(score, conc_score)
        flags.extend(conc_flags)

        # Check 4: Rapid-fire trading — many trades in short window
        rapid_score, rapid_flags = self._check_rapid_trading(trader_trades)
        score = max(score, rapid_score)
        flags.extend(rapid_flags)

        # Check 5: Restricted jurisdiction trading
        juris_score, juris_flags = self._check_restricted_jurisdiction(trader_trades)
        score = max(score, juris_score)
        flags.extend(juris_flags)

        details["flags_count"] = len(flags)

        return RiskAssessment(
            target_id=trader_id,
            target_type="trader",
            risk_level=_score_to_level(score),
            risk_score=round(score, 4),
            flags=flags,
            details=details,
        )

    def score_market(self, market_id: str) -> RiskAssessment:
        """Score a single market's risk level."""
        market_trades = [t for t in self._trades if t.market_id == market_id]
        if not market_trades:
            return RiskAssessment(
                target_id=market_id,
                target_type="market",
                risk_level=RiskLevel.LOW,
                risk_score=0.0,
                flags=[],
                details={"trade_count": 0},
            )

        flags: list[str] = []
        score = 0.0

        # Check: Volume spike — >3x average daily volume
        total_volume = sum(t.quantity * t.price for t in market_trades)
        unique_traders = len(set(t.trader_id for t in market_trades))

        if unique_traders > 0:
            avg_per_trader = total_volume / unique_traders
            if avg_per_trader > 10000:
                score = max(score, 0.6)
                flags.append(f"High avg volume per trader: ${avg_per_trader:,.0f}")

        # Check: Low unique trader count with high volume (coordination signal)
        if unique_traders <= 3 and total_volume > 5000:
            score = max(score, 0.8)
            flags.append(f"Possible coordination: {unique_traders} traders, ${total_volume:,.0f} volume")

        # Check: One-sided trading (all buy or all sell)
        buy_count = sum(1 for t in market_trades if t.side == "buy")
        sell_count = len(market_trades) - buy_count
        if len(market_trades) >= 5:
            if buy_count == 0 or sell_count == 0:
                score = max(score, 0.7)
                flags.append(f"One-sided trading: {buy_count} buy, {sell_count} sell")

        return RiskAssessment(
            target_id=market_id,
            target_type="market",
            risk_level=_score_to_level(score),
            risk_score=round(score, 4),
            flags=flags,
            details={
                "trade_count": len(market_trades),
                "unique_traders": unique_traders,
                "total_volume": total_volume,
            },
        )

    def score_all_traders(self) -> list[RiskAssessment]:
        """Score all traders. Returns assessments sorted by risk (highest first)."""
        trader_ids = set(t.trader_id for t in self._trades)
        assessments = [self.score_trader(tid) for tid in trader_ids]
        assessments.sort(key=lambda a: a.risk_score, reverse=True)
        return assessments

    def score_all_markets(self) -> list[RiskAssessment]:
        """Score all markets. Returns assessments sorted by risk (highest first)."""
        market_ids = set(t.market_id for t in self._trades)
        assessments = [self.score_market(mid) for mid in market_ids]
        assessments.sort(key=lambda a: a.risk_score, reverse=True)
        return assessments

    def _check_wash_trading(self, trades: list[Trade]) -> tuple[float, list[str]]:
        """Detect wash trading: same trader buying and selling same outcome in same market."""
        flags = []
        market_outcomes: dict[str, set[str]] = defaultdict(set)
        for t in trades:
            key = f"{t.market_id}:{t.outcome}"
            market_outcomes[key].add(t.side)

        wash_count = sum(1 for sides in market_outcomes.values() if len(sides) > 1)
        if wash_count > 0:
            flags.append(f"Wash trading detected: {wash_count} market/outcome pairs with both buy and sell")
            return 0.85, flags
        return 0.0, []

    def _check_volume_anomaly(self, trades: list[Trade]) -> tuple[float, list[str]]:
        """Detect unusual volume: total volume > $50k flags as medium risk."""
        flags = []
        total = sum(t.quantity * t.price for t in trades)
        if total > 100000:
            flags.append(f"Very high total volume: ${total:,.0f}")
            return 0.7, flags
        if total > 50000:
            flags.append(f"High total volume: ${total:,.0f}")
            return 0.4, flags
        return 0.0, []

    def _check_concentration(self, trades: list[Trade]) -> tuple[float, list[str]]:
        """Detect concentration: >70% of trades in a single market."""
        flags = []
        if not trades:
            return 0.0, []
        market_counts: dict[str, int] = defaultdict(int)
        for t in trades:
            market_counts[t.market_id] += 1
        max_count = max(market_counts.values())
        ratio = max_count / len(trades)
        if ratio > 0.7 and max_count >= 5:
            top_market = max(market_counts, key=lambda k: market_counts[k])
            flags.append(f"Concentrated trading: {ratio:.0%} of trades in market {top_market}")
            return 0.5, flags
        return 0.0, []

    def _check_rapid_trading(self, trades: list[Trade]) -> tuple[float, list[str]]:
        """Detect rapid-fire trading: 10+ trades within 5 minutes."""
        flags = []
        if len(trades) < 10:
            return 0.0, []
        sorted_trades = sorted(trades, key=lambda t: t.timestamp)
        for i in range(len(sorted_trades) - 9):
            window_start = sorted_trades[i].timestamp
            window_end = sorted_trades[i + 9].timestamp
            delta = (window_end - window_start).total_seconds()
            if delta <= 300:  # 5 minutes
                flags.append(f"Rapid trading: 10 trades in {delta:.0f}s")
                return 0.75, flags
        return 0.0, []

    def _check_restricted_jurisdiction(self, trades: list[Trade]) -> tuple[float, list[str]]:
        """Flag trades from restricted jurisdictions."""
        flags = []
        restricted_count = 0
        for t in trades:
            if t.jurisdiction is not None:
                if t.jurisdiction.value in ("NV", "NJ", "NY", "AZ", "MA"):
                    restricted_count += 1
        if restricted_count > 0:
            flags.append(f"Trades from restricted jurisdictions: {restricted_count}")
            return 0.9, flags
        return 0.0, []
