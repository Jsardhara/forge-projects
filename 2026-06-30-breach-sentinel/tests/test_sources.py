"""Tests for LocalSource parsing + HIBP offline degradation."""

from breach_sentinel.models import BreachType
from breach_sentinel.sources import HIBPSource, LocalSource


def test_local_source_finds_email(local_source):
    recs = local_source.query("alice@example.com", BreachType.EMAIL)
    assert len(recs) == 1
    assert recs[0].breach_name == "Adobe 2013"
    assert recs[0].breach_date.year == 2013


def test_local_source_matches_case_insensitively(local_source):
    recs = local_source.query("ALICE@Example.com")
    assert len(recs) == 2  # email + password for alice


def test_local_source_no_false_positive(local_source):
    recs = local_source.query("nobody@nowhere.com")
    assert recs == []


def test_local_source_handles_jsonl(tmp_path):
    p = tmp_path / "b.jsonl"
    p.write_text(
        '{"identity_value": "z@z.com", "breach_type": "email", "breach_name": "X", "breach_date": "2020-01-01"}\n',
        encoding="utf-8",
    )
    src = LocalSource(sid="l", path=str(p))
    recs = src.query("z@z.com")
    assert len(recs) == 1


def test_local_source_dedupes_same_bid(local_source):
    # alice appears once for Adobe; duplicate bid not re-added
    recs = local_source.query("alice@example.com")
    bids = [r.bid for r in recs]
    assert len(bids) == len(set(bids))


def test_hibp_without_key_returns_empty():
    src = HIBPSource(api_key=None)
    assert src.query("anyone@example.com") == []


def test_hibp_supports_multiple_values():
    src = HIBPSource(api_key="dummy")
    # Without network these just return []; we only assert no crash and correct type.
    assert isinstance(src.query("a@b.com"), list)
