"""Tests for the high-level AgeVerifier."""

import time

import pytest

from zkage_verify.verifier import AgeVerifier
from zkage_verify.models import AgeThreshold, AgeCredential


class TestAgeVerifierIssueCredential:
    def test_issue_credential(self):
        verifier = AgeVerifier(current_year=2026)
        cred = verifier.issue_credential(
            subject_id="user-1",
            birth_year=2000,
            issuer_id="gov",
        )
        assert cred.subject_id == "user-1"
        assert cred.birth_year == 2000
        assert cred.issuer_id == "gov"
        assert cred.issued_at > 0
        assert cred.expires_at > cred.issued_at

    def test_default_issuer(self):
        verifier = AgeVerifier(current_year=2026)
        cred = verifier.issue_credential(subject_id="u", birth_year=2000)
        assert cred.issuer_id == "zkage-default-issuer"

    def test_default_ttl(self):
        """Default TTL should be approximately 1 year."""
        verifier = AgeVerifier(current_year=2026)
        cred = verifier.issue_credential(subject_id="u", birth_year=2000)
        ttl = cred.expires_at - cred.issued_at
        assert 86400 * 360 <= ttl <= 86400 * 370  # ~1 year


class TestAgeVerifierVerify:
    def test_adult_passes(self):
        """2000 birth year in 2026 = 26 years old, passes ADULT (18)."""
        verifier = AgeVerifier(current_year=2026)
        cred = verifier.issue_credential(subject_id="u", birth_year=2000)
        result = verifier.verify(cred, AgeThreshold.ADULT)
        assert result.is_valid is True
        assert result.threshold_met is True
        assert result.proof_valid is True
        assert result.nullifier is not None

    def test_coppa_passes(self):
        """2015 birth year in 2026 = 11 years old, fails COPPA (13)."""
        verifier = AgeVerifier(current_year=2026)
        cred = verifier.issue_credential(subject_id="u", birth_year=2015)
        result = verifier.verify(cred, AgeThreshold.COPPA)
        assert result.is_valid is False
        assert result.threshold_met is False

    def test_coppa_passes_for_teen(self):
        """2010 birth year in 2026 = 16 years old, passes COPPA (13)."""
        verifier = AgeVerifier(current_year=2026)
        cred = verifier.issue_credential(subject_id="u", birth_year=2010)
        result = verifier.verify(cred, AgeThreshold.COPPA)
        assert result.is_valid is True

    def test_alcohol_us_passes(self):
        """2000 birth year in 2026 = 26 years old, passes ALCOHOL_US (21)."""
        verifier = AgeVerifier(current_year=2026)
        cred = verifier.issue_credential(subject_id="u", birth_year=2000)
        result = verifier.verify(cred, AgeThreshold.ALCOHOL_US)
        assert result.is_valid is True

    def test_alcohol_us_fails_for_teen(self):
        """2010 birth year in 2026 = 16 years old, fails ALCOHOL_US (21)."""
        verifier = AgeVerifier(current_year=2026)
        cred = verifier.issue_credential(subject_id="u", birth_year=2010)
        result = verifier.verify(cred, AgeThreshold.ALCOHOL_US)
        assert result.is_valid is False

    def test_exact_threshold_boundary(self):
        """Birth year exactly at threshold boundary."""
        # Born 2008 in 2026 = exactly 18 years old
        verifier = AgeVerifier(current_year=2026)
        cred = verifier.issue_credential(subject_id="u", birth_year=2008)
        result = verifier.verify(cred, AgeThreshold.ADULT)
        assert result.is_valid is True

    def test_one_year_too_young(self):
        """Born 2009 in 2026 = 17 years old, fails ADULT (18)."""
        verifier = AgeVerifier(current_year=2026)
        cred = verifier.issue_credential(subject_id="u", birth_year=2009)
        result = verifier.verify(cred, AgeThreshold.ADULT)
        assert result.is_valid is False
        assert result.threshold_met is False


class TestAgeVerifierNullifier:
    def test_double_spend_blocked(self):
        """Same credential cannot be verified twice."""
        verifier = AgeVerifier(current_year=2026)
        cred = verifier.issue_credential(subject_id="u", birth_year=2000)
        
        result1 = verifier.verify(cred, AgeThreshold.ADULT)
        assert result1.is_valid is True
        
        result2 = verifier.verify(cred, AgeThreshold.ADULT)
        assert result2.is_valid is False
        assert result2.nullifier_spent is True

    def test_nullifier_set_tracks_spent(self):
        verifier = AgeVerifier(current_year=2026)
        cred = verifier.issue_credential(subject_id="u", birth_year=2000)
        
        assert verifier.nullifier_set.size == 0
        verifier.verify(cred, AgeThreshold.ADULT)
        assert verifier.nullifier_set.size == 1

    def test_different_credentials_different_nullifiers(self):
        """Two different users should have independent nullifiers."""
        verifier = AgeVerifier(current_year=2026)
        cred1 = verifier.issue_credential(subject_id="u1", birth_year=2000)
        cred2 = verifier.issue_credential(subject_id="u2", birth_year=1995)
        
        result1 = verifier.verify(cred1, AgeThreshold.ADULT)
        result2 = verifier.verify(cred2, AgeThreshold.ADULT)
        
        assert result1.is_valid is True
        assert result2.is_valid is True
        assert result1.nullifier.value != result2.nullifier.value
        assert verifier.nullifier_set.size == 2


class TestAgeVerifierExpiry:
    def test_expired_credential_fails(self):
        """Expired credential should fail verification."""
        verifier = AgeVerifier(current_year=2026)
        cred = AgeCredential(
            subject_id="u",
            birth_year=2000,
            issued_at=1000000000,  # 2001
            expires_at=1100000000,  # 2004 — expired long ago
            issuer_id="gov",
        )
        result = verifier.verify(cred, AgeThreshold.ADULT)
        assert result.is_valid is False
        assert "expired" in result.message.lower()

    def test_not_yet_valid_fails(self):
        """Credential with future issue date should fail."""
        verifier = AgeVerifier(current_year=2026)
        future = int(time.time()) + 86400 * 365  # 1 year from now
        cred = AgeCredential(
            subject_id="u",
            birth_year=2000,
            issued_at=future,
            expires_at=future + 86400 * 365,
            issuer_id="gov",
        )
        result = verifier.verify(cred, AgeThreshold.ADULT)
        assert result.is_valid is False
        assert "not yet valid" in result.message.lower()


class TestAgeVerifierCustomNullifierSet:
    def test_shared_nullifier_set_across_verifiers(self):
        """Two verifiers sharing a nullifier set should detect cross-service reuse."""
        from zkage_verify.nullifier import NullifierSet
        shared_ns = NullifierSet()
        
        verifier1 = AgeVerifier(current_year=2026, nullifier_set=shared_ns)
        verifier2 = AgeVerifier(current_year=2026, nullifier_set=shared_ns)
        
        cred = verifier1.issue_credential(subject_id="u", birth_year=2000)
        
        # First verifier succeeds
        result1 = verifier1.verify(cred, AgeThreshold.ADULT)
        assert result1.is_valid is True
        
        # Second verifier (different service) detects reuse
        result2 = verifier2.verify(cred, AgeThreshold.ADULT)
        assert result2.is_valid is False
        assert result2.nullifier_spent is True
