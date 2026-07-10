"""Tests for the EgressFilter allowlist logic."""
import pytest

from agentvault.egress import EgressFilter, EgressRule
from agentvault.vault import EgressDeniedError


def test_empty_filter_is_default_deny():
    f = EgressFilter()
    assert f.allow("api.github.com") is False
    assert f.allow("127.0.0.1") is False


def test_exact_host_match():
    f = EgressFilter([EgressRule("api.alpaca.markets")])
    assert f.allow("api.alpaca.markets") is True
    assert f.allow("evil.example.com") is False


def test_wildcard_prefix_match():
    f = EgressFilter([EgressRule("*.github.com")])
    assert f.allow("api.github.com") is True
    assert f.allow("github.com") is True
    assert f.allow("evil.gitlab.com") is False


def test_case_insensitive():
    f = EgressFilter([EgressRule("API.Alpaca.Markets")])
    assert f.allow("api.alpaca.markets") is True


def test_port_restriction():
    f = EgressFilter([EgressRule("api.github.com", ports=(443,))])
    assert f.allow("api.github.com", 443) is True
    assert f.allow("api.github.com", 8080) is False
    # None port means "don't care" caller -> allowed when no port constraint on rule
    assert f.allow("api.github.com", None) is True


def test_cidr_match():
    f = EgressFilter([EgressRule("10.0.0.0/8")])
    assert f.allow("10.1.2.3", 443) is True
    assert f.allow("192.168.0.1", 443) is False


def test_cidr_with_port():
    f = EgressFilter([EgressRule("10.0.0.0/8", ports=(5432,))])
    assert f.allow("10.0.0.5", 5432) is True
    assert f.allow("10.0.0.5", 80) is False


def test_check_raises_on_deny():
    f = EgressFilter([EgressRule("api.github.com")])
    f.check("api.github.com")  # no raise
    with pytest.raises(EgressDeniedError):
        f.check("evil.example.com")


def test_add_rule_returns_rule():
    f = EgressFilter()
    r = f.add_rule("*.example.com")
    assert isinstance(r, EgressRule)
    assert f.allow("sub.example.com") is True


def test_multiple_rules_any_match():
    f = EgressFilter([EgressRule("a.com"), EgressRule("b.com")])
    assert f.allow("b.com") is True
    assert f.allow("c.com") is False


def test_to_jsonable_roundtrip_shape():
    f = EgressFilter([EgressRule("x.com", ports=(443,))])
    j = f.to_jsonable()
    assert j == [{"pattern": "x.com", "ports": [443]}]
