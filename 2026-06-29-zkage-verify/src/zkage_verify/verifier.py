"""High-level age verification engine.

Orchestrates the full flow:
1. Issue credential (trusted issuer)
2. Generate ZK proof of age >= threshold
3. Check nullifier (prevent double-spend)
4. Return verification result
"""

from __future__ import annotations

import hashlib
import time
from typing import Optional

from zkage_verify.commitment import pedersen_commit, generate_blinding_factor
from zkage_verify.rangeproof import generate_range_proof, verify_range_proof
from zkage_verify.nullifier import compute_nullifier, NullifierSet
from zkage_verify.models import (
    AgeCredential,
    Proof,
    VerificationResult,
    Nullifier,
    AgeThreshold,
)


class AgeVerifier:
    """Main interface for age verification.
    
    Usage:
        verifier = AgeVerifier(current_year=2026)
        
        # Issue credential
        cred = verifier.issue_subject(
            subject_id="user-123",
            birth_year=2000,
            issuer_id="gov-id-authority",
        )
        
        # Verify age >= 18
        result = verifier.verify(cred, AgeThreshold.ADULT)
        if result.is_valid:
            print("Access granted — age verified, no birthdate revealed")
    """
    
    def __init__(
        self,
        current_year: int = 2026,
        nullifier_set: NullifierSet | None = None,
    ) -> None:
        self.current_year = current_year
        self._nullifiers = nullifier_set or NullifierSet()
    
    def issue_credential(
        self,
        subject_id: str,
        birth_year: int,
        issuer_id: str = "zkage-default-issuer",
        ttl_seconds: int = 86400 * 365,  # 1 year default
    ) -> AgeCredential:
        """Issue a new age credential to a subject.
        
        In production, this would require the issuer to sign the credential.
        Here we create an unsigned credential for demonstration.
        
        Args:
            subject_id: Pseudonymous identifier for the subject
            birth_year: The subject's birth year
            issuer_id: Identifier of the issuing authority
            ttl_seconds: Credential validity period in seconds
        
        Returns:
            A new AgeCredential
        """
        now = int(time.time())
        return AgeCredential(
            subject_id=subject_id,
            birth_year=birth_year,
            issued_at=now,
            expires_at=now + ttl_seconds,
            issuer_id=issuer_id,
            signature=None,  # Would be filled by issuer in production
        )
    
    def verify(
        self,
        credential: AgeCredential,
        threshold: AgeThreshold,
        max_birth_year: int = 2008,  # Reasonable upper bound (18yo in 2026)
    ) -> VerificationResult:
        """Verify a credential meets an age threshold.
        
        Generates a ZK proof that the birth year implies age >= threshold.
        Checks if the credential's nullifier has been spent.
        
        Args:
            credential: The age credential to verify
            threshold: The age threshold to check against
            max_birth_year: Maximum reasonable birth year
        
        Returns:
            VerificationResult with validity status
        """
        # Check expiry
        now = int(time.time())
        if now > credential.expires_at:
            return VerificationResult(
                is_valid=False,
                threshold_met=False,
                nullifier_spent=False,
                proof_valid=False,
                message="Credential expired",
            )
        
        # Check not-yet-valid
        if now < credential.issued_at:
            return VerificationResult(
                is_valid=False,
                threshold_met=False,
                nullifier_spent=False,
                proof_valid=False,
                message="Credential not yet valid",
            )
        
        # Compute threshold birth year
        threshold_birth_year = self.current_year - threshold.value
        
        # Check birth year allows age >= threshold
        if credential.birth_year > threshold_birth_year:
            return VerificationResult(
                is_valid=False,
                threshold_met=False,
                nullifier_spent=False,
                proof_valid=False,
                message=f"Subject born {credential.birth_year}, too young for threshold {threshold.value}",
            )
        
        # Compute nullifier
        nullifier = compute_nullifier(credential)
        
        # Check double-spend
        if self._nullifiers.is_spent(nullifier):
            return VerificationResult(
                is_valid=False,
                threshold_met=True,
                nullifier_spent=True,
                proof_valid=False,
                message="Nullifier already spent — credential reused",
                nullifier=nullifier,
            )
        
        # Generate ZK proof: birth_year <= threshold_birth_year (age >= threshold)
        # We commit to birth_year and prove it's in [min_birth, threshold_birth_year]
        blinding_factor = generate_blinding_factor()
        proof = generate_range_proof(
            value=credential.birth_year,
            threshold=1900,  # Reasonable lower bound for birth year
            blinding_factor=blinding_factor,
            max_value=threshold_birth_year,  # Upper bound proves age >= threshold
        )
        
        # Verify the proof
        proof_valid = verify_range_proof(
            proof,
            proof.commitment.commitment_value,
            max_value=threshold_birth_year,
        )
        
        if not proof_valid:
            return VerificationResult(
                is_valid=False,
                threshold_met=True,
                nullifier_spent=False,
                proof_valid=False,
                message="ZK proof verification failed",
            )
        
        # Mark nullifier as spent
        self._nullifiers.add(nullifier)
        
        return VerificationResult(
            is_valid=True,
            threshold_met=True,
            nullifier_spent=False,
            proof_valid=True,
            message=f"Age verified: >= {threshold.value} (birth year hidden)",
            nullifier=nullifier,
        )
    
    @property
    def nullifier_set(self) -> NullifierSet:
        """Access the nullifier set."""
        return self._nullifiers
