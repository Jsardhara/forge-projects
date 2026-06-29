"""Nullifier scheme for preventing double-spending of age credentials.

A nullifier is a unique, deterministic derivative of a credential that:
1. Cannot be linked back to the credential (one-way hash)
2. Is unique per credential (same credential always produces same nullifier)
3. Reveals nothing about the underlying identity

This prevents a user from verifying the same credential multiple times
to different service providers.
"""

from __future__ import annotations

import hashlib
from typing import Set

from zkage_verify.models import Nullifier, AgeCredential


def compute_nullifier(
    credential: AgeCredential,
    service_id: str = "",
) -> Nullifier:
    """Compute a nullifier from a credential.
    
    The nullifier is derived from:
    - The credential's subject_id
    - The credential's issuer_id
    - The birth_year (via commitment, not raw)
    - Optional service_id (for service-specific nullifiers)
    
    Args:
        credential: The age credential
        service_id: Optional service identifier for scoped nullifiers
    
    Returns:
        A Nullifier object
    """
    # Create a commitment hash of the credential
    cred_data = (
        f"{credential.subject_id}:{credential.issuer_id}:"
        f"{credential.birth_year}:{credential.issued_at}:"
        f"{credential.expires_at}"
    ).encode()
    cred_hash = hashlib.sha256(cred_data).hexdigest()

    # Derive nullifier from credential hash + service context
    nullifier_input = f"nullifier:{cred_hash}:{service_id}".encode()
    nullifier_value = hashlib.sha256(nullifier_input).hexdigest()

    return Nullifier(
        value=nullifier_value,
        credential_hash=cred_hash,
    )


def compute_nullifier_from_secret(
    secret: str,
    salt: str,
) -> str:
    """Compute a nullifier directly from a secret and salt.
    
    Useful for stateless scenarios where you don't have a full credential.
    
    Args:
        secret: The secret (e.g., credential ID)
        salt: A service-specific salt
    
    Returns:
        Hex-encoded nullifier string
    """
    data = f"nullifier:{secret}:{salt}".encode()
    return hashlib.sha256(data).hexdigest()


class NullifierSet:
    """Tracks spent nullifiers to prevent double-spending.
    
    In production this would be a Merkle tree or a distributed set.
    In-memory version for demonstration and testing.
    """
    
    def __init__(self) -> None:
        self._spent: Set[str] = set()
    
    def add(self, nullifier: Nullifier) -> None:
        """Mark a nullifier as spent."""
        self._spent.add(nullifier.value)
    
    def is_spent(self, nullifier: Nullifier | str) -> bool:
        """Check if a nullifier has been spent."""
        if isinstance(nullifier, Nullifier):
            return nullifier.value in self._spent
        return nullifier in self._spent
    
    def remove(self, nullifier: Nullifier | str) -> bool:
        """Remove a nullifier (for rollback scenarios).
        
        Returns True if the nullifier was present and removed.
        """
        val = nullifier.value if isinstance(nullifier, Nullifier) else nullifier
        if val in self._spent:
            self._spent.remove(val)
            return True
        return False
    
    @property
    def size(self) -> int:
        """Number of spent nullifiers."""
        return len(self._spent)
    
    @property
    def spent_values(self) -> frozenset[str]:
        """Return an immutable view of spent nullifiers."""
        return frozenset(self._spent)
    
    def clear(self) -> None:
        """Clear all spent nullifiers."""
        self._spent.clear()
