"""Tests for Signal Feed core modules."""

import pytest
from signal_feed.analyzer import score_sentiment, classify_category


class TestSentimentAnalysis:
    def test_bullish_text(self):
        score, label = score_sentiment("Bitcoin surges to all-time high as institutional adoption accelerates")
        assert score > 0.3
        assert label == "bullish"

    def test_bearish_text(self):
        score, label = score_sentiment("Crypto market crash continues as major exchange hack causes panic selling")
        assert score < -0.3
        assert label == "bearish"

    def test_neutral_text(self):
        score, label = score_sentiment("The Federal Reserve met today to discuss monetary policy.")
        assert label == "neutral"

    def test_empty_text(self):
        score, label = score_sentiment("")
        assert score == 0.0
        assert label == "neutral"

    def test_score_bounds(self):
        """Scores should always be in [-1, 1]."""
        scores = [
            score_sentiment("moon rocket surge all-time high bull run institutional adoption")[0],
            score_sentiment("crash collapse hack bankrupt liquidated rug pull")[0],
        ]
        for s in scores:
            assert -1.0 <= s <= 1.0

    def test_mixed_sentiment(self):
        """Mixed bullish and bearish signals should partially cancel."""
        score, label = score_sentiment("Bitcoin surges but market crash fears remain")
        # Should be moderate magnitude due to mixed signals
        assert abs(score) < 0.8


class TestCategoryClassification:
    def test_crypto_category(self):
        assert classify_category("Bitcoin breaks $100k resistance") == "crypto"
        assert classify_category("Ethereum DeFi TVL reaches new high") == "crypto"

    def test_stocks_category(self):
        assert classify_category("S&P 500 hits record high on strong earnings") == "stocks"
        assert classify_category("Nasdaq IPO exceeds expectations") == "stocks"

    def test_general_category(self):
        assert classify_category("The economy is showing mixed signals") == "general"

    def test_crypto_overrides_stocks(self):
        """If both crypto and stock keywords present, crypto wins."""
        result = classify_category("Bitcoin and S&P 500 both surge today")
        assert result == "crypto"


class TestAnalyzerEdgeCases:
    def test_case_insensitive(self):
        score1, _ = score_sentiment("BITCOIN SURGES")
        score2, _ = score_sentiment("bitcoin surges")
        assert score1 == score2

    def test_repeated_keywords(self):
        """Repeated keywords shouldn't inflate score beyond bounds."""
        score, _ = score_sentiment("surge surge surge surge surge")
        assert -1.0 <= score <= 1.0
