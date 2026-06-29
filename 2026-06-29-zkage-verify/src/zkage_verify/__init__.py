"""zkage-verify — Privacy-preserving age verification with ZK proof primitives.

Provides cryptographic primitives for proving age thresholds without
revealing exact birthdate. Uses Pedersen commitments and a simplified
Bulletproofs-style range proof over elliptic curve groups.

All operations use the secp256k1 curve via the `hashlib` + `hmac`
stdlib modules — no external dependencies.
"""

from zkage_verify.models import (
    AgeCredential,
    Commitment,
    Proof,
    VerificationResult,
    Nullifier,
    AgeThreshold,
)
from zkage_verify.commitment import (
    pedersen_commit,
    pedersen_verify,
    generate_blinding_factor,
)
from zkage_verify.rangeproof import (
    generate_range_proof,
    verify_range_proof,
)
from zkage_verify.nullifier import (
    compute_nullifier,
    NullifierSet,
)
from zkage_verify.verifier import AgeVerifier

__all__ = [
    "AgeCredential",
    "Commitment",
    "Proof",
    "VerificationResult",
    "Nullifier",
    "AgeThreshold",
    "pedersen_commit",
    "pedersen_verify",
    "generate_blinding_factor",
    "generate_range_proof",
    "verify_range_proof",
    "compute_nullifier",
    "NullifierSet",
    "AgeVerifier",
]

__version__ = "0.1.0"
