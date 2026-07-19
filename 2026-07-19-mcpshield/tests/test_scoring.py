from mcpshield.scoring import score_findings
from mcpshield.models import Finding


def _f(sev):
    return Finding(probe="p", severity=sev, title="t", detail="d")


def test_score_zero_pass():
    score, band = score_findings([_f("INFO"), _f("INFO")])
    assert score == 0
    assert band == "PASS"


def test_score_low_pass():
    score, band = score_findings([_f("LOW")])
    assert score == 2
    assert band == "PASS"


def test_score_high_warns():
    score, band = score_findings([_f("HIGH")])
    assert band == "WARN"
    assert score == 12


def test_score_medium_under_warn_pass():
    # two MEDIUM = 10, below WARN_RISK_AT (20) and no HIGH/CRITICAL -> PASS
    score, band = score_findings([_f("MEDIUM"), _f("MEDIUM")])
    assert score == 10
    assert band == "PASS"


def test_score_medium_over_warn():
    # five MEDIUM = 25 -> >= WARN_RISK_AT
    score, band = score_findings([_f("MEDIUM") for _ in range(5)])
    assert score == 25
    assert band == "WARN"


def test_score_critical_fails():
    score, band = score_findings([_f("CRITICAL")])
    assert band == "FAIL"


def test_score_high_with_mediums_fails_at_50():
    # 4 HIGH = 48 -> WARN; 5 HIGH = 60 -> FAIL (>=50)
    score, band = score_findings([_f("HIGH") for _ in range(4)])
    assert band == "WARN"
    score, band = score_findings([_f("HIGH") for _ in range(5)])
    assert band == "FAIL"


def test_score_capped_at_100():
    score, _ = score_findings([_f("CRITICAL") for _ in range(10)])
    assert score == 100
