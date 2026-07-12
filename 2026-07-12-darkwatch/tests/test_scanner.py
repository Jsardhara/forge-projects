"""Tests for scanner orchestration + banding + checklist."""
from __future__ import annotations

from darkwatch.models import ComplianceBand, Regulation  # noqa: E402
from darkwatch.scanner import (  # noqa: E402
    band_for,
    regulation_checklist,
    scan_html,
)
from fixtures import (  # noqa: E402
    CLEAN_HTML,
    HEAVY_HTML,
    MINOR_ADDICTIVE_HTML,
    PRECHECKED_HTML,
    ROACH_MOTEL_HTML,
)


def test_scan_clean_is_compliant():
    r = scan_html(CLEAN_HTML, "clean")
    assert r.band == ComplianceBand.COMPLIANT
    assert r.findings == []


def test_scan_roach_motel_needs_review_or_worse():
    r = scan_html(ROACH_MOTEL_HTML, "roach")
    assert r.band in (ComplianceBand.NEEDS_REVIEW, ComplianceBand.NON_COMPLIANT)
    assert any(f.rule_id == "roach_motel_cancel" for f in r.findings)


def test_scan_prechecked_fires():
    r = scan_html(PRECHECKED_HTML, "pre")
    assert any(f.rule_id == "prechecked_optin" for f in r.findings)


def test_scan_minor_addictive_fires():
    r = scan_html(MINOR_ADDICTIVE_HTML, "minor")
    assert any(f.rule_id == "minor_addictive" for f in r.findings)


def test_scan_heavy_is_non_compliant():
    r = scan_html(HEAVY_HTML, "heavy")
    assert r.band == ComplianceBand.NON_COMPLIANT
    assert len(r.findings) >= 3


def test_band_for_empty():
    assert band_for([]) == ComplianceBand.COMPLIANT


def test_band_for_single_medium():
    from darkwatch.models import Finding, Severity

    f = Finding(
        rule_id="x", title="t", description="d",
        regulation=Regulation.EU_UCPD, severity=Severity.MEDIUM, evidence="e",
    )
    assert band_for([f]) == ComplianceBand.NEEDS_REVIEW


def test_band_for_three_lows_non_compliant():
    from darkwatch.models import Finding, Severity

    fs = [
        Finding(rule_id="a", title="t", description="d", regulation=Regulation.EU_UCPD,
                severity=Severity.LOW, evidence="e"),
        Finding(rule_id="b", title="t", description="d", regulation=Regulation.EU_DSA,
                severity=Severity.LOW, evidence="e"),
        Finding(rule_id="c", title="t", description="d", regulation=Regulation.FTC_NEGATIVE_OPTION,
                severity=Severity.LOW, evidence="e"),
    ]
    assert band_for(fs) == ComplianceBand.NON_COMPLIANT


def test_band_for_one_critical_non_compliant():
    from darkwatch.models import Finding, Severity

    f = Finding(rule_id="a", title="t", description="d", regulation=Regulation.NYC_SUBSCRIPTIONS,
                severity=Severity.CRITICAL, evidence="e")
    assert band_for([f]) == ComplianceBand.NON_COMPLIANT


def test_checklist_covers_four_regulations():
    checks = regulation_checklist(CLEAN_HTML, "clean")
    assert len(checks) == 4
    assert {c.regulation for c in checks} == set(Regulation)


def test_checklist_pass_on_clean():
    checks = regulation_checklist(CLEAN_HTML, "clean")
    assert all(c.status == "pass" for c in checks)


def test_checklist_fail_on_heavy():
    checks = regulation_checklist(HEAVY_HTML, "heavy")
    assert any(c.status == "fail" for c in checks)


def test_summary_counts():
    r = scan_html(HEAVY_HTML, "heavy")
    s = r.summary()
    assert s["total"] == len(r.findings)
    assert sum(s["by_severity"].values()) == s["total"]
