"""Tests for data models."""

from zkage_verify.models import (
    AgeCredential,
    AgeThreshold,
    Commitment,
    Nullifier,
    Proof,
    VerificationResult,
)


class TestAgeThreshold:
    def test_coppa_value(self):
        assert AgeThreshold.COPPA.value == 13

    def test_teen_value(self):
        assert AgeThreshold.TEEN.value == 16

    def test_adult_value(self):
        assert AgeThreshold.ADULT.value == 18

    def test_alcohol_us_value(self):
        assert AgeThreshold.ALCOHOL_US.value == 21

    def test_enum_lookup_by_name(self):
        assert AgeThreshold["COPPA"] is AgeThreshold.COPPA
        assert AgeThreshold["ADULT"] is AgeThreshold.ADULT


class TestCommitment:
    def test_frozen_dataclass(self):
        comm = Commitment(value=2000, blinding_factor=42, commitment_value=12345)
        assert comm.value == 2000
        assert comm.blinding_factor == 42
        assert comm.commitment_value == 12345

    def test_immutability(self):
        comm = Commitment(value=2000, blinding_factor=42, commitment_value=12345)
        try:
            comm.value = 1999
            assert False, "Should have raised FrozenInstanceError"
        except AttributeError:
            pass  # Expected — dataclass is frozen


class TestAgeCredential:
    def test_creation(self):
        cred = AgeCredential(
            subject_id="user-1",
            birth_year=2000,
            issued_at=1719000000,
            expires_at=1750536000,
            issuer_id="gov",
        )
        assert cred.subject_id == "user-1"
        assert cred.birth_year == 2000
        assert cred.signature is None

    def test_with_signature(self):
        cred = AgeCredential(
            subject_id="user-1",
            birth_year=2000,
            issued_at=1719000000,
            expires_at=1750536000,
            issuer_id="gov",
            signature="abc123",
        )
        assert cred.signature == "abc123"

    def test_equality(self):
        cred1 = AgeCredential(
            subject_id="user-1", birth_year=2000,
            issued_at=1000, expires_at=2000, issuer_id="gov",
        )
        cred2 = AgeCredential(
            subject_id="user-1", birth_year=2000,
            issued_at=1000, expires_at=2000, issuer_id="gov",
        )
        assert cred1 == cred2

    def test_inequality(self):
        cred1 = AgeCredential(
            subject_id="user-1", birth_year=2000,
            issued_at=1000, expires_at=2000, issuer_id="gov",
        )
        cred2 = AgeCredential(
            subject_id="user-2", birth_year=2000,
            issued_at=1000, expires_at=2000, issuer_id="gov",
        )
        assert cred1 != cred2


class TestNullifier:
    def test_creation(self):
        n = Nullifier(value="abc123", credential_hash="def456")
        assert n.value == "abc123"
        assert n.credential_hash == "def456"

    def test_immutability(self):
        n = Nullifier(value="abc", credential_hash="def")
        try:
            n.value = "xyz"
            assert False, "Should have raised FrozenInstanceError"
        except AttributeError:
            pass


class TestProof:
    def test_creation(self):
        comm = Commitment(value=2000, blinding_factor=42, commitment_value=999)
        proof = Proof(
            commitment=comm,
            threshold=18,
            proof_data={"challenge": 123},
            timestamp=1719000000,
        )
        assert proof.commitment.value == 2000
        assert proof.threshold == 18
        assert proof.timestamp == 1719000000

    def test_immutability(self):
        comm = Commitment(value=2000, blinding_factor=42, commitment_value=999)
        proof = Proof(
            commitment=comm, threshold=18,
            proof_data={}, timestamp=1000,
        )
        try:
            proof.threshold = 99
            assert False, "Should have raised FrozenInstanceError"
        except AttributeError:
            pass


class TestVerificationResult:
    def test_valid_result(self):
        n = Nullifier(value="n1", credential_hash="c1")
        result = VerificationResult(
            is_valid=True,
            threshold_met=True,
            nullifier_spent=False,
            proof_valid=True,
            message="OK",
            nullifier=n,
        )
        assert result.is_valid is True
        assert result.nullifier.value == "n1"

    def test_invalid_result_no_nullifier(self):
        result = VerificationResult(
            is_valid=False,
            threshold_met=False,
            nullifier_spent=False,
            proof_valid=False,
            message="Too young",
        )
        assert result.is_valid is False
        assert result.nullifier is None
