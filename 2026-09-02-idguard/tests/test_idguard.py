"""idguard test suite. Bare module imports (no tests. prefix)."""

from idguard.engine import aggregate, exit_code, scan_record
from idguard.notify import REAL_STATES, build_notification_plan, lookup_state
from idguard.patterns import (
    detect_dl,
    detect_dob,
    detect_email,
    detect_phone,
    normalize_ssn,
    validate_ssn,
)


# ---------------- SSN validation ----------------
def test_ssn_valid_classic():
    ok, normalized = validate_ssn("123-45-6789")
    assert ok is True
    assert normalized == "123456789"
    assert normalize_ssn("123 45 6789") == "123456789"


def test_ssn_invalid_rules():
    assert validate_ssn("078-05-1120")[0] is False  # advertising number
    assert validate_ssn("666-12-3456")[0] is False  # area 666 never issued
    assert validate_ssn("000-12-3456")[0] is False  # area 000
    assert validate_ssn("900-12-3456")[0] is False  # area 900+ reserved
    assert validate_ssn("123-00-6789")[0] is False  # group 00
    assert validate_ssn("123-45-0000")[0] is False  # serial 0000
    assert validate_ssn("219-09-9999")[0] is False  # advertising block


def test_ssn_wrong_len_and_alpha():
    assert validate_ssn("123-45-678")[0] is False
    assert validate_ssn("ABC-DE-FGHI")[0] is False


# ---------------- US DL per-state detection ----------------
def test_dl_california_format():
    assert "CA" in detect_dl("1A2345678")
    assert "CA" in detect_dl("123456789")  # CA also issues 9-digit


def test_dl_florida_format():
    assert "FL" in detect_dl("A123456789012")
    assert "MI" in detect_dl("A123456789012")  # FL & MI share the classic format


def test_dl_texas_format():
    assert "TX" in detect_dl("12A345678")


def test_dl_new_york_format():
    assert "NY" in detect_dl("B12345678")


def test_dl_generic_fallback():
    assert detect_dl("X7Q42ZZ") == ["generic"]
    assert detect_dl("") == []


def test_dl_not_an_identity_claim():
    # a bare 9-digit string matches several classic formats -> multiple hints
    hits = detect_dl("123456789")
    assert isinstance(hits, list) and len(hits) >= 3
    assert "generic" not in hits


# ---------------- plain PII detectors ----------------
def test_email_phone_dob():
    assert detect_email("user@example.com") is True
    assert detect_email("not-an-email") is False
    assert detect_phone("(555) 010-1234") is True
    assert detect_dob("1991-04-12") is True
    assert detect_dob("04/12/1991") is True
    assert detect_dob("last-week") is False


# ---------------- record severity composition ----------------
def test_crit_full_triple():
    r = scan_record(0, {"name": "Jane Doe", "dob": "1991-04-12",
                        "ssn": "123-45-6789"})
    assert r.severity == "CRIT"
    assert "ssn_valid" in r.present_assets


def test_crit_ssn_plus_name():
    r = scan_record(1, {"first": "Bob", "ssn": "123-45-6789"})
    assert r.severity == "CRIT"


def test_high_ssn_alone():
    r = scan_record(2, {"ssn": "123-45-6789"})
    assert r.severity == "HIGH"


def test_high_dl_name_dob():
    r = scan_record(3, {"name": "Jane Doe", "dob": "1991-04-12",
                        "dl": "A123456789012"})
    assert r.severity == "HIGH"


def test_medium_dl_name():
    r = scan_record(4, {"name": "J Smith", "dl": "12A345678"})
    assert r.severity == "MEDIUM"


def test_medium_password_and_low_email():
    assert scan_record(5, {"password": "hunter2"}).severity == "MEDIUM"
    assert scan_record(6, {"email": "a@b.com"}).severity == "LOW"


def test_invalid_ssn_does_not_crit():
    r = scan_record(7, {"name": "Jane Doe", "dob": "1991-04-12",
                        "ssn": "666-12-3456"})
    assert r.severity != "CRIT"


# ---------------- aggregate + exit gate ----------------
def test_aggregate_counts_and_exit():
    results = [
        scan_record(0, {"ssn": "123-45-6789", "name": "X", "dob": "1990-01-01"}),
        scan_record(1, {"ssn": "123-45-6789"}),
        scan_record(2, {"email": "a@b.com"}),
    ]
    t = aggregate(results, total_scanned=3)
    assert t.scanned == 3
    assert t.count_by_severity.get("CRIT") == 1
    assert t.count_by_severity.get("HIGH") == 1
    assert t.count_by_severity.get("LOW") == 1
    assert t.exposed_ssns == 2
    assert t.critical_ids == [0]
    assert exit_code(t) == 2


def test_exit_high_threshold():
    t = aggregate([scan_record(0, {"ssn": "123-45-6789"})], total_scanned=1)
    assert exit_code(t) == 1
    assert exit_code(t, warn_threshold=99) == 0  # high tolerated


def test_exit_clean():
    t = aggregate([scan_record(0, {"email": "a@b.com"})], total_scanned=1)
    assert exit_code(t) == 0


# ---------------- notification matrix ----------------
def test_matrix_covers_states():
    assert len(REAL_STATES) >= 50
    for code in ("CA", "TX", "NY", "FL", "VT", "MD", "WA"):
        assert code in REAL_STATES
        e = lookup_state(code)
        assert "days" in e and "note" in e


def test_plan_emits_rows_and_checklists():
    plan = build_notification_plan(state_codes=["CA", "FL"], affected_subscribers=10)
    assert "CA" in plan and "FL" in plan
    assert "not legal advice" in plan.lower()
    assert "Notification letter" in plan
    assert "Remediation steps" in plan
    assert "credit freeze" in plan.lower()


def test_plan_default_covers_all():
    plan = build_notification_plan()
    for code in ("CA", "VT"):
        assert f"| {code} |" in plan


def test_lookup_unknown_state():
    import pytest
    with pytest.raises(KeyError):
        lookup_state("XX")