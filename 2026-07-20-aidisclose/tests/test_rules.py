"""Integrity tests for the curated mandate dataset."""
from aidisclose.models import MandateStatus, Severity
from aidisclose.rules import load_mandates


def test_dataset_nonempty():
    m = load_mandates()
    assert len(m) >= 5


def test_unique_mids():
    mids = [x.mid for x in load_mandates()]
    assert len(mids) == len(set(mids)), "duplicate mandate ids"


def test_each_mandate_well_formed():
    for m in load_mandates():
        assert m.title and m.summary and m.source
        assert m.jurisdiction
        assert len(m.obligations) >= 1
        codes = [o.code for o in m.obligations]
        assert len(codes) == len(set(codes)), f"dup obligation code in {m.mid}"
        for o in m.obligations:
            assert o.severity in Severity
            assert o.weight > 0


def test_status_distribution():
    statuses = {m.status for m in load_mandates()}
    assert MandateStatus.IN_FORCE in statuses
    # at least one proposed/monitor entry to exercise the watch path
    assert MandateStatus.PROPOSED in statuses or MandateStatus.UPCOMING in statuses


def test_effective_dates_parseable():
    for m in load_mandates():
        if m.effective_date is not None:
            assert m.effective_date.year > 2000
