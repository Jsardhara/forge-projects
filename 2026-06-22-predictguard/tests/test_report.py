"""Tests for PredictGuard report generator."""

from datetime import datetime, timezone
from predictguard.models import (
    Trade, ComplianceReport, RiskAssessment, RiskLevel, Jurisdiction
)
from predictguard.report import ReportGenerator


def _make_trade(tid, trader, market="M001", side="buy", outcome="Yes",
                price=0.5, quantity=10, platform="kalshi",
                jurisdiction=None):
    return Trade(
        tid=tid, market_id=market, trader_id=trader,
        side=side, outcome=outcome, price=price, quantity=quantity,
        platform=platform, jurisdiction=jurisdiction,
    )


class TestReportGenerator:
    def test_generate_empty(self):
        gen = ReportGenerator()
        now = datetime.now(timezone.utc)
        report = gen.generate([], [], now, now)
        assert report.total_trades == 0
        assert report.compliance_score == 1.0
        assert len(report.findings) == 0

    def test_generate_with_clean_trades(self):
        gen = ReportGenerator()
        now = datetime.now(timezone.utc)
        trades = [
            _make_trade("T1", "alice", jurisdiction=Jurisdiction.CALIFORNIA),
            _make_trade("T2", "bob", jurisdiction=Jurisdiction.TEXAS),
        ]
        report = gen.generate(trades, [], now, now)
        assert report.total_trades == 2
        assert report.compliance_score == 1.0

    def test_generate_with_flagged_trades(self):
        gen = ReportGenerator()
        now = datetime.now(timezone.utc)
        trades = [
            _make_trade("T1", "eve", jurisdiction=Jurisdiction.NEVADA, price=0.8, quantity=100),
        ]
        risk = [
            RiskAssessment(
                target_id="eve", target_type="trader",
                risk_level=RiskLevel.CRITICAL, risk_score=0.9,
                flags=["Restricted jurisdiction"],
            )
        ]
        report = gen.generate(trades, risk, now, now)
        assert report.flagged_trades == 1
        assert report.compliance_score < 1.0
        assert len(report.findings) > 0

    def test_generate_with_critical_risk(self):
        gen = ReportGenerator()
        now = datetime.now(timezone.utc)
        trades = [_make_trade("T1", "alice")]
        risk = [
            RiskAssessment(
                target_id="alice", target_type="trader",
                risk_level=RiskLevel.CRITICAL, risk_score=0.95,
                flags=["Wash trading"],
            )
        ]
        report = gen.generate(trades, risk, now, now)
        assert report.compliance_score < 0.85
        assert any("CRITICAL" in f for f in report.findings)

    def test_generate_with_high_risk(self):
        gen = ReportGenerator()
        now = datetime.now(timezone.utc)
        trades = [_make_trade("T1", "alice")]
        risk = [
            RiskAssessment(
                target_id="alice", target_type="trader",
                risk_level=RiskLevel.HIGH, risk_score=0.7,
                flags=["High volume"],
            )
        ]
        report = gen.generate(trades, risk, now, now)
        assert any("HIGH" in f for f in report.findings)
        assert any("24 hours" in r for r in report.recommendations)


class TestFormatReport:
    def test_format_text(self):
        now = datetime.now(timezone.utc)
        report = ComplianceReport(
            rid="RPT-000001",
            generated_at=now,
            period_start=now,
            period_end=now,
            jurisdiction=Jurisdiction.CALIFORNIA,
            total_trades=100,
            total_volume=50000.0,
            flagged_trades=2,
            compliance_score=0.85,
            findings=["High flagged ratio"],
            recommendations=["Review flagged trades"],
        )
        text = ReportGenerator.format_report(report)
        assert "RPT-000001" in text
        assert "85%" in text or "0.85" in text
        assert "High flagged ratio" in text
        assert "Review flagged trades" in text

    def test_format_empty_findings(self):
        now = datetime.now(timezone.utc)
        report = ComplianceReport(
            rid="RPT-000002",
            generated_at=now,
            period_start=now,
            period_end=now,
            compliance_score=1.0,
        )
        text = ReportGenerator.format_report(report)
        assert "None" in text
