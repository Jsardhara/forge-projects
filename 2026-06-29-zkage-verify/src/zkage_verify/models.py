"""Data models for zkage-verify.

Frozen dataclasses for all cryptographic objects — immutable by design.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class AgeThreshold(Enum):
    """Common age thresholds for compliance."""
    COPPA = 13        # US Children's Online Privacy Protection Act
    TEEN = 16         # EU GDPR digital consent age (varies by member state)
    ADULT = 18        # US adult content / gambling
    ALCOHOL_US = 21   # US alcohol/tobacco


@dataclass(frozen=True)
class Commitment:
    """A Pedersen commitment to a secret value.
    
    commitment = g^value * h^blinding_factor  (mod p)
    """
    value: int          # The committed value (e.g., birth year)
    blinding_factor: int
    commitment_value: int  # The actual commitment (g^v * h^b mod p)


@dataclass(frozen=True)
class Proof:
    """A range proof that committed value >= threshold without revealing value."""
    commitment: Commitment
    threshold: int
    proof_data: dict  # Proof components (simplified Bulletproofs-style)
    timestamp: int    # Unix timestamp of proof generation


@dataclass(frozen=True)
class AgeCredential:
    """An age credential issued by a trusted authority."""
    subject_id: str           # Pseudonymous identifier
    birth_year: int           # Actual birth year (kept secret)
    issued_at: int            # Unix timestamp of issuance
    expires_at: int           # Unix timestamp of expiry
    issuer_id: str            # Trusted issuer identifier
    signature: Optional[str] = None  # Issuer signature (hex)


@dataclass(frozen=True)
class Nullifier:
    """A unique nullifier derived from a credential — prevents double-spending."""
    value: str  # Hex-encoded nullifier hash
    credential_hash: str  # Hash of the credential this nullifier belongs to


@dataclass(frozen=True)
class VerificationResult:
    """Result of an age verification attempt."""
    is_valid: bool
    threshold_met: bool
    nullifier_spent: bool
    proof_valid: bool
    message: str
    nullifier: Optional[Nullifier] = None
