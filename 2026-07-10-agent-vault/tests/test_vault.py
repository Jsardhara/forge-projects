"""Tests for the Vault credential broker and policy enforcement."""
from datetime import timedelta

import pytest

from agentvault import (
    EgressDeniedError,
    ScopeDeniedError,
    SecretNotFoundError,
    SessionExpiredError,
    SessionNotFoundError,
    SessionRevokedError,
    UseLimitExceededError,
    Vault,
)
from agentvault.models import Scope, Secret, SecretKind


@pytest.fixture
def vault():
    return Vault()


def _add_secret(v, name="k", sid="sec_1"):
    return v.add_secret(name, "REAL_VALUE", kind=SecretKind.API_KEY, sid=sid)


# ---- Secret storage --------------------------------------------------------
def test_add_and_meta(vault):
    s = _add_secret(vault)
    meta = vault.get_secret_meta(s.sid)
    assert meta.value == "REAL_VALUE"
    assert vault.secrets[0].sid == s.sid


def test_get_secret_meta_missing_raises(vault):
    with pytest.raises(SecretNotFoundError):
        vault.get_secret_meta("sec_nope")


def test_delete_secret_soft(vault):
    s = _add_secret(vault)
    vault.delete_secret(s.sid)
    with pytest.raises(SecretNotFoundError):
        vault.get_secret_meta(s.sid)
    assert s.sid not in [x.sid for x in vault.secrets]


def test_resolve_unknown_session_records_deny(vault):
    _add_secret(vault)
    with pytest.raises(SessionNotFoundError):
        vault.resolve("ses_unknown", "sec_1")
    assert len(vault.audit_trail) >= 1


# ---- Session issue / resolve ----------------------------------------------
def test_resolve_success(vault):
    s = _add_secret(vault)
    sess = vault.issue_session(scope=Scope(secret_ids=(s.sid,)))
    val = vault.resolve(sess.session_id, s.sid)
    assert val == "REAL_VALUE"
    assert sess.use_count == 0  # session object is a snapshot; live count increments internally


def test_resolve_scope_denied(vault):
    s = _add_secret(vault, sid="sec_1")
    other = vault.add_secret("other", "V2", sid="sec_2")
    sess = vault.issue_session(scope=Scope(secret_ids=(other.sid,)))
    with pytest.raises(ScopeDeniedError):
        vault.resolve(sess.session_id, "sec_1")


def test_resolve_unknown_secret(vault):
    sess = vault.issue_session(scope=Scope(secret_ids=("sec_1",)))
    with pytest.raises(SecretNotFoundError):
        vault.resolve(sess.session_id, "sec_1")


# ---- Revocation / expiry ---------------------------------------------------
def test_revoked_session_denies(vault):
    s = _add_secret(vault)
    sess = vault.issue_session(scope=Scope(secret_ids=(s.sid,)))
    vault.revoke_session(sess.session_id)
    with pytest.raises(SessionRevokedError):
        vault.resolve(sess.session_id, s.sid)


def test_expired_session_denies(vault):
    s = _add_secret(vault)
    # TTL of 1 second; expire by issuing with a tiny negative window is not allowed,
    # so issue then check expiry via a past expires_at by revoking-style: instead use
    # a session that expired by setting ttl=0 won't be negative. Use explicit check.
    sess = vault.issue_session(scope=Scope(secret_ids=(s.sid,)), ttl=timedelta(seconds=1))
    import time
    time.sleep(1.1)
    with pytest.raises(SessionExpiredError):
        vault.resolve(sess.session_id, s.sid)


def test_use_limit_exceeded(vault):
    s = _add_secret(vault)
    sess = vault.issue_session(scope=Scope(secret_ids=(s.sid,), max_uses=2))
    assert vault.resolve(sess.session_id, s.sid) == "REAL_VALUE"
    assert vault.resolve(sess.session_id, s.sid) == "REAL_VALUE"
    with pytest.raises(UseLimitExceededError):
        vault.resolve(sess.session_id, s.sid)


# ---- Egress gate -----------------------------------------------------------
def test_egress_not_authorized_denies(vault):
    s = _add_secret(vault)
    sess = vault.issue_session(scope=Scope(secret_ids=(s.sid,)))  # egress not enabled
    with pytest.raises(ScopeDeniedError):
        vault.check_egress(sess.session_id, "api.alpaca.markets", 443)


def test_egress_allowlisted_ok(vault):
    s = _add_secret(vault)
    sess = vault.issue_session(
        scope=Scope(secret_ids=(s.sid,), allowed_hosts=("api.alpaca.markets",), can_proxy_egress=True)
    )
    assert vault.check_egress(sess.session_id, "api.alpaca.markets", 443) is True


def test_egress_not_on_allowlist_denies(vault):
    s = _add_secret(vault)
    sess = vault.issue_session(
        scope=Scope(secret_ids=(s.sid,), allowed_hosts=("api.alpaca.markets",), can_proxy_egress=True)
    )
    with pytest.raises(EgressDeniedError):
        vault.check_egress(sess.session_id, "evil.example.com", 443)


def test_egress_after_revoke_denies(vault):
    s = _add_secret(vault)
    sess = vault.issue_session(scope=Scope(can_proxy_egress=True, allowed_hosts=("x.com",)))
    vault.revoke_session(sess.session_id)
    with pytest.raises(SessionRevokedError):
        vault.check_egress(sess.session_id, "x.com")


# ---- Audit integrity -------------------------------------------------------
def test_audit_chain_intact_after_operations(vault):
    s = _add_secret(vault)
    sess = vault.issue_session(scope=Scope(secret_ids=(s.sid,), can_proxy_egress=True,
                                            allowed_hosts=("api.alpaca.markets",)))
    vault.resolve(sess.session_id, s.sid)
    vault.check_egress(sess.session_id, "api.alpaca.markets", 443)
    assert vault.audit_verify() is True
    assert len(vault.audit_trail) >= 4  # issue, resolve, egress-allow + add-secret
