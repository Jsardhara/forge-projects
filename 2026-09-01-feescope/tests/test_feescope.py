from feescope import FeeScopeScanner, ScanConfig
from feescope.models import FeeItem, Severity, Verdict


def _media(
    line_id,
    amount,
    verified=None,
    description="Media placement",
    category="media",
    attached_to=None,
):
    return FeeItem(
        line_id=line_id,
        description=description,
        amount=amount,
        category=category,
        verified=verified,
        attached_to=attached_to,
    )


def _fee(line_id, amount, description, attached_to=None):
    return FeeItem(
        line_id=line_id,
        description=description,
        amount=amount,
        category="fee",
        attached_to=attached_to,
    )


# ---- FEE-002 hidden surcharge ----------------------------------------------

def test_hidden_surcharge_flags():
    sc = FeeScopeScanner()
    items = [
        _media("L1", 120.0, verified=100.0),
        _media("L2", 500.0, verified=500.0),
    ]
    r = sc.scan(items)
    assert r.verdict == Verdict.FLAG
    codes = {f.code for f in r.findings}
    assert "FEE-002" in codes
    assert any(f.line_id == "L1" for f in r.findings)


def test_no_surcharge_within_tolerance():
    sc = FeeScopeScanner()
    items = [_media("L1", 100.0, verified=100.4)]  # +0.4% < 0.5% tolerance
    r = sc.scan(items)
    assert not any(f.code == "FEE-002" for f in r.findings)
    assert r.verdict == Verdict.CLEAR


def test_missing_verified_is_clear():
    sc = FeeScopeScanner()
    items = [_media("L1", 250.0)]  # no verified source -> no surcharge signal
    r = sc.scan(items)
    assert r.verdict == Verdict.CLEAR


# ---- FEE-001 opaque fee -----------------------------------------------------

def test_opaque_fee_warns():
    sc = FeeScopeScanner()
    items = [_fee("F1", 40.0, "Platform fee")]
    r = sc.scan(items)
    assert any(f.code == "FEE-001" for f in r.findings)
    assert r.verdict == Verdict.WARN


def test_transparent_fee_not_opaque():
    sc = FeeScopeScanner()
    items = [_fee("F1", 40.0, "Third-party ad verification fee")]
    r = sc.scan(items)
    assert not any(f.code == "FEE-001" for f in r.findings)


def test_empty_description_fee_is_opaque():
    sc = FeeScopeScanner()
    items = [_fee("F1", 12.50, "")]
    r = sc.scan(items)
    assert any(f.code == "FEE-001" for f in r.findings)


# ---- FEE-003 fee stacking ---------------------------------------------------

def test_fee_stacking_warns():
    sc = FeeScopeScanner()
    items = [
        _media("B1", 1000.0),
        _fee("F1", 50.0, "Platform fee", attached_to="B1"),
        _fee("F2", 30.0, "Processing fee", attached_to="B1"),
    ]
    r = sc.scan(items)
    assert any(f.code == "FEE-003" for f in r.findings)
    assert r.verdict == Verdict.WARN


def test_single_fee_no_stacking():
    sc = FeeScopeScanner()
    items = [
        _media("B1", 1000.0),
        _fee("F1", 50.0, "Third-party verification fee", attached_to="B1"),
    ]
    r = sc.scan(items)
    assert not any(f.code == "FEE-003" for f in r.findings)
    assert r.verdict == Verdict.CLEAR


# ---- FEE-004 fee ratio ------------------------------------------------------

def test_fee_ratio_warns_when_over_cap():
    sc = FeeScopeScanner()
    items = [
        _media("B1", 100.0),
        _media("B2", 1000.0),
        _fee("F1", 330.0, "Platform fee"),  # 330/1100 = 0.30 > 0.20
    ]
    r = sc.scan(items)
    assert any(f.code == "FEE-004" for f in r.findings)


def test_fee_ratio_clear_under_cap():
    sc = FeeScopeScanner()
    items = [
        _media("B1", 1000.0),
        _fee("F1", 100.0, "Platform fee"),  # 100/1100 = 0.091 < 0.20
    ]
    r = sc.scan(items)
    assert not any(f.code == "FEE-004" for f in r.findings)


# ---- FEE-005 reconciliation -------------------------------------------------

def test_recon_mismatch_flags():
    sc = FeeScopeScanner()
    items = [_media("L1", 120.0), _media("L2", 300.0)]  # sum 420 vs expected 350 = 16.7%
    r = sc.scan(items, expected_total=350.0)
    assert any(f.code == "FEE-005" and f.severity == Severity.FLAG for f in r.findings)
    assert r.verdict == Verdict.FLAG


def test_recon_small_drift_warns():
    sc = FeeScopeScanner()
    items = [_media("L1", 1200.0)]
    r = sc.scan(items, expected_total=1208.0)  # 8/1208 = 0.66% > 0.5%, < 5%
    assert any(f.code == "FEE-005" and f.severity == Severity.WARN for f in r.findings)


def test_recon_within_tolerance_clear():
    sc = FeeScopeScanner()
    items = [_media("L1", 1000.0)]
    r = sc.scan(items, expected_total=1000.3)  # 0.3/1000 = 0.03% < 0.5%
    assert not any(f.code == "FEE-005" for f in r.findings)
    assert r.verdict == Verdict.CLEAR


# ---- severity dominance / score ----------------------------------------------

def test_verdict_is_severity_dominant_not_score_sum():
    # one WARN + one FLAG -> verdict FLAG, not CLEAR/WARN
    sc = FeeScopeScanner()
    items = [
        _media("L1", 120.0, verified=100.0),  # FLAG
        _fee("F1", 20.0, "Platform fee"),      # WARN
    ]
    r = sc.scan(items)
    assert r.verdict == Verdict.FLAG
    assert any(f.severity == Severity.FLAG for f in r.findings)


def test_score_is_weighted_magnitude():
    sc = FeeScopeScanner()
    items = [_media("L1", 120.0, verified=100.0)]  # single FLAG -> 55
    r = sc.scan(items)
    assert r.score == 55.0


def test_clean_invoice():
    sc = FeeScopeScanner()
    items = [
        _media("L1", 1000.0, verified=1000.0, description="Programmatic media buy"),
        _fee("F1", 40.0, "Third-party verification fee"),
    ]
    r = sc.scan(items)
    assert r.findings == []
    assert r.verdict == Verdict.CLEAR
    assert r.score == 0.0


# ---- config override --------------------------------------------------------

def test_custom_max_fee_ratio():
    sc = FeeScopeScanner(ScanConfig(max_fee_ratio=0.05))
    items = [
        _media("B1", 1000.0),
        _fee("F1", 100.0, "Platform fee"),  # 0.091 > 0.05
    ]
    r = sc.scan(items)
    assert any(f.code == "FEE-004" for f in r.findings)