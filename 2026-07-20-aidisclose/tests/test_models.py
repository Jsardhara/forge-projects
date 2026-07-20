"""Unit tests for aidisclose models."""
from datetime import date

from aidisclose.models import (
    Mandate, MandateStatus, Obligation, OrgProfile, Severity,
)

from fixtures import make_profile


def test_obligation_weight_mapping():
    assert Obligation("a", "A", "x", Severity.CRITICAL).weight == 10
    assert Obligation("a", "A", "x", Severity.HIGH).weight == 6
    assert Obligation("a", "A", "x", Severity.MEDIUM).weight == 3
    assert Obligation("a", "A", "x", Severity.LOW).weight == 1


def test_mandate_sector_scope():
    m = Mandate(mid="x", jurisdiction="US-NY", title="t", summary="s",
                scope_sectors=("employment",),
                obligations=(Obligation("o", "O", "x"),))
    assert m.sector_applies({"employment"})
    assert not m.sector_applies({"retail"})
    # None scope => applies to all sectors
    m2 = Mandate(mid="y", jurisdiction="US-NY", title="t", summary="s",
                 scope_sectors=None,
                 obligations=(Obligation("o", "O", "x"),))
    assert m2.sector_applies({"anything"})


def test_mandate_use_scope():
    m = Mandate(mid="x", jurisdiction="US-NY", title="t", summary="s",
                scope_uses=("hiring", "biometric"),
                obligations=(Obligation("o", "O", "x"),))
    assert m.use_applies({"hiring"})
    assert m.use_applies({"biometric"})
    assert not m.use_applies({"customer_support"})
    # None scope => applies to any use
    m2 = Mandate(mid="y", jurisdiction="US-NY", title="t", summary="s",
                 scope_uses=None,
                 obligations=(Obligation("o", "O", "x"),))
    assert m2.use_applies({"anything"})


def test_profile_set_helpers():
    p = make_profile(sectors=["employment"], jurisdictions=["US-NY"],
                     ai_uses=["hiring"], implemented=["audit"])
    assert p.sectors_set() == {"employment"}
    assert p.jurisdictions_set() == {"US-NY"}
    assert p.uses_set() == {"hiring"}
    assert p.implemented_set() == {"audit"}


def test_mid_is_used_not_builtin_id():
    m = Mandate(mid="nyc-ll144", jurisdiction="US-NY", title="t", summary="s",
                obligations=(Obligation("o", "O", "x"),))
    assert m.mid == "nyc-ll144"
    # mid attribute works; builtin id() is untouched
    assert isinstance(id(m), int)
