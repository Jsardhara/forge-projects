"""Tests for Pedersen commitment scheme."""

from zkage_verify.commitment import (
    generate_blinding_factor,
    get_generators,
    get_prime,
    pedersen_commit,
    pedersen_verify,
)


class TestBlindingFactor:
    def test_generates_in_range(self):
        for _ in range(10):
            bf = generate_blinding_factor()
            p = get_prime()
            assert 1 <= bf <= p - 1

    def test_generates_unique(self):
        factors = {generate_blinding_factor() for _ in range(100)}
        assert len(factors) == 100  # All unique

    def test_randomness(self):
        # Two blinding factors should be different
        bf1 = generate_blinding_factor()
        bf2 = generate_blinding_factor()
        assert bf1 != bf2


class TestPedersenCommitment:
    def test_commit_produces_commitment(self):
        comm, bf = pedersen_commit(2000)
        assert comm > 0
        assert bf > 0

    def test_same_value_different_blinding(self):
        """Same value with different blinding factors should produce different commitments."""
        comm1, _ = pedersen_commit(2000, blinding_factor=42)
        comm2, _ = pedersen_commit(2000, blinding_factor=999)
        assert comm1 != comm2

    def test_different_value_same_blinding(self):
        """Different values with same blinding should produce different commitments."""
        comm1, _ = pedersen_commit(2000, blinding_factor=42)
        comm2, _ = pedersen_commit(1999, blinding_factor=42)
        assert comm1 != comm2

    def test_verify_correct_opening(self):
        value = 2000
        comm, bf = pedersen_commit(value)
        assert pedersen_verify(comm, value, bf) is True

    def test_verify_wrong_value_fails(self):
        comm, bf = pedersen_commit(2000)
        assert pedersen_verify(comm, 1999, bf) is False

    def test_verify_wrong_blinding_fails(self):
        comm, bf = pedersen_commit(2000)
        assert pedersen_verify(comm, 2000, bf + 1) is False

    def test_commitment_in_prime_field(self):
        comm, _ = pedersen_commit(2000)
        p = get_prime()
        assert comm < p

    def test_auto_blinding_factor(self):
        """When no blinding factor is provided, one is generated."""
        comm, bf = pedersen_commit(2000)
        assert bf > 0
        assert pedersen_verify(comm, 2000, bf) is True

    def test_large_value(self):
        """Commit to a large value (birth year far in past)."""
        comm, bf = pedersen_commit(1900)
        assert pedersen_verify(comm, 1900, bf) is True

    def test_zero_value(self):
        """Should work with value=0 (edge case)."""
        comm, bf = pedersen_commit(0)
        assert pedersen_verify(comm, 0, bf) is True


class TestGenerators:
    def test_generators_are_distinct(self):
        g, h = get_generators()
        assert g != h

    def test_generators_in_range(self):
        g, h = get_generators()
        p = get_prime()
        assert 1 < g < p - 1
        assert 1 < h < p - 1

    def test_prime_is_large(self):
        p = get_prime()
        assert p > 2**255  # At least 256-bit prime


class TestHomomorphicProperty:
    """Pedersen commitments are homomorphic: C(v1) * C(v2) = C(v1+v2)."""
    
    def test_homomorphic_addition(self):
        p = get_prime()
        comm1, bf1 = pedersen_commit(1000)
        comm2, bf2 = pedersen_commit(500)
        
        # Combined commitment
        combined_value = 1500
        combined_bf = (bf1 + bf2) % (p - 1)
        combined_comm, _ = pedersen_commit(combined_value, combined_bf)
        
        # Product of individual commitments
        product = (comm1 * comm2) % p
        
        assert combined_comm == product
