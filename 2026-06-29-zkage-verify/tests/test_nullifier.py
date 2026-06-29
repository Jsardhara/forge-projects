"""Tests for nullifier scheme."""

from zkage_verify.nullifier import (
    NullifierSet,
    compute_nullifier,
    compute_nullifier_from_secret,
)
from zkage_verify.models import AgeCredential, Nullifier


def _make_cred(subject_id="user-1", birth_year=2000):
    return AgeCredential(
        subject_id=subject_id,
        birth_year=birth_year,
        issued_at=1719000000,
        expires_at=1750536000,
        issuer_id="gov",
    )


class TestComputeNullifier:
    def test_deterministic(self):
        """Same credential always produces same nullifier."""
        cred = _make_cred()
        n1 = compute_nullifier(cred)
        n2 = compute_nullifier(cred)
        assert n1.value == n2.value
        assert n1.credential_hash == n2.credential_hash

    def test_different_credentials_different_nullifiers(self):
        cred1 = _make_cred(subject_id="user-1")
        cred2 = _make_cred(subject_id="user-2")
        n1 = compute_nullifier(cred1)
        n2 = compute_nullifier(cred2)
        assert n1.value != n2.value

    def test_different_birth_years_different_nullifiers(self):
        cred1 = _make_cred(birth_year=2000)
        cred2 = _make_cred(birth_year=2001)
        n1 = compute_nullifier(cred1)
        n2 = compute_nullifier(cred2)
        assert n1.value != n2.value

    def test_service_scoped_nullifiers(self):
        """Same credential with different service_id produces different nullifiers."""
        cred = _make_cred()
        n1 = compute_nullifier(cred, service_id="service-a")
        n2 = compute_nullifier(cred, service_id="service-b")
        assert n1.value != n2.value

    def test_nullifier_is_hex_string(self):
        cred = _make_cred()
        n = compute_nullifier(cred)
        # Should be a valid hex string
        int(n.value, 16)  # Raises ValueError if not hex
        assert len(n.value) == 64  # SHA-256 hex digest

    def test_credential_hash_is_hex(self):
        cred = _make_cred()
        n = compute_nullifier(cred)
        int(n.credential_hash, 16)
        assert len(n.credential_hash) == 64


class TestComputeNullifierFromSecret:
    def test_deterministic(self):
        n1 = compute_nullifier_from_secret("secret-123", "salt-456")
        n2 = compute_nullifier_from_secret("secret-123", "salt-456")
        assert n1 == n2

    def test_different_secrets(self):
        n1 = compute_nullifier_from_secret("secret-1", "salt")
        n2 = compute_nullifier_from_secret("secret-2", "salt")
        assert n1 != n2

    def test_different_salts(self):
        n1 = compute_nullifier_from_secret("secret", "salt-1")
        n2 = compute_nullifier_from_secret("secret", "salt-2")
        assert n1 != n2


class TestNullifierSet:
    def test_empty_set(self):
        ns = NullifierSet()
        assert ns.size == 0
        assert ns.is_spent("anything") is False

    def test_add_and_check(self):
        ns = NullifierSet()
        n = Nullifier(value="abc123", credential_hash="def456")
        ns.add(n)
        assert ns.is_spent(n) is True
        assert ns.is_spent("abc123") is True
        assert ns.size == 1

    def test_not_spent(self):
        ns = NullifierSet()
        n = Nullifier(value="abc", credential_hash="def")
        assert ns.is_spent(n) is False

    def test_add_multiple(self):
        ns = NullifierSet()
        for i in range(10):
            ns.add(Nullifier(value=f"nul-{i}", credential_hash=f"cred-{i}"))
        assert ns.size == 10

    def test_remove(self):
        ns = NullifierSet()
        n = Nullifier(value="abc", credential_hash="def")
        ns.add(n)
        assert ns.remove(n) is True
        assert ns.is_spent(n) is False
        assert ns.size == 0

    def test_remove_nonexistent(self):
        ns = NullifierSet()
        n = Nullifier(value="abc", credential_hash="def")
        assert ns.remove(n) is False

    def test_clear(self):
        ns = NullifierSet()
        for i in range(5):
            ns.add(Nullifier(value=f"nul-{i}", credential_hash=f"cred-{i}"))
        ns.clear()
        assert ns.size == 0

    def test_spent_values_immutable_view(self):
        ns = NullifierSet()
        ns.add(Nullifier(value="a", credential_hash="b"))
        values = ns.spent_values
        assert "a" in values
        # The frozenset itself can't be modified
        try:
            values.add("c")
            assert False, "Should raise AttributeError"
        except AttributeError:
            pass

    def test_double_add_same_nullifier(self):
        """Adding the same nullifier twice doesn't increase size."""
        ns = NullifierSet()
        n = Nullifier(value="abc", credential_hash="def")
        ns.add(n)
        ns.add(n)
        assert ns.size == 1
