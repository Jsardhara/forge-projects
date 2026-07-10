"""Tests for the tamper-evident audit trail."""
import pytest

from agentvault.audit import AuditEntry, AuditTrail


def _record_n(trail: AuditTrail, n: int) -> None:
    for i in range(n):
        trail.record("ses_x", "resolve", f"sec_{i}", "ok")


def test_record_assigns_seq_and_hashes():
    t = AuditTrail()
    e = t.record("s1", "resolve", "sec_1", "ok")
    assert e.seq == 1
    assert e.entry_hash  # non-empty
    assert e.entry_hash == e.compute_hash()
    assert len(t) == 1


def test_chain_links_prev_hash():
    t = AuditTrail()
    a = t.record("s", "resolve", "sec", "ok")
    b = t.record("s", "resolve", "sec", "ok2")
    assert b.prev_hash == a.entry_hash
    assert t.verify() is True


def test_verify_true_on_clean():
    t = AuditTrail()
    _record_n(t, 5)
    assert t.verify() is True
    assert t.tampered_at() is None


def test_verify_detects_tamper():
    t = AuditTrail()
    _record_n(t, 3)
    # Mutate an early entry's detail (simulate log tampering). Because entries are
    # frozen dataclasses, we reconstruct via replace-like mutation through internals.
    entries = t.entries
    # Simulate editing the stored entry's detail by rebuilding the list with a changed copy.
    import dataclasses
    tampered = dataclasses.replace(entries[0], detail="ALTERED")
    object.__setattr__(t, "_entries", [tampered] + list(entries[1:]))
    # Recompute chain: entry 0 hash now invalid vs a recompute; verify should fail.
    assert t.verify() is False
    assert t.tampered_at() == 1


def test_first_entry_prev_is_genesis():
    t = AuditTrail()
    e = t.record("s", "resolve", "sec", "ok")
    assert e.prev_hash == "GENESIS"


def test_entries_immutable_copy():
    t = AuditTrail()
    t.record("s", "resolve", "sec", "ok")
    out = t.entries
    assert out is not t.entries  # returns a fresh list each access
