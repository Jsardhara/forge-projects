"""Pedersen commitment scheme over a prime-order group.

Pedersen commitments are:
- Perfectly hiding (commitment reveals nothing about value)
-Computationally binding (cannot open to a different value)

We use a deterministic construction from SHA-256 to derive group
parameters, avoiding the need for an external crypto library.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from typing import Tuple

# A large prime for our group (close to 2^256)
# This is the secp256k1 field prime
_P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F


def _derive_generator(seed: bytes) -> int:
    """Derive a group generator deterministically from a seed string.
    
    Uses SHA-256 to produce a value in [1, P-1].
    """
    h = hashlib.sha256(seed).digest()
    val = int.from_bytes(h, "big") % (_P - 1) + 1
    return val


# Generator g — derived deterministically from "zkage-verify-g"
_G = _derive_generator(b"zkage-verify-g")

# Second generator h — derived from "zkage-verify-h" (nothing-up-my-sleeve)
_H = _derive_generator(b"zkage-verify-h")


def generate_blinding_factor() -> int:
    """Generate a cryptographically secure random blinding factor.
    
    Returns an integer in [1, P-1].
    """
    # Generate 32 random bytes, reduce to group element
    raw = secrets.token_bytes(32)
    return int.from_bytes(raw, "big") % (_P - 1) + 1


def pedersen_commit(value: int, blinding_factor: int | None = None) -> Tuple[int, int]:
    """Create a Pedersen commitment to `value`.
    
    commitment = g^value * h^blinding_factor  (mod P)
    
    Args:
        value: The secret value to commit to
        blinding_factor: Optional blinding factor (generated if None)
    
    Returns:
        Tuple of (commitment_value, blinding_factor)
    """
    if blinding_factor is None:
        blinding_factor = generate_blinding_factor()
    
    # g^value mod P
    gv = pow(_G, value, _P)
    # h^blinding_factor mod P
    hb = pow(_H, blinding_factor, _P)
    # commitment = g^v * h^b mod P
    commitment_value = (gv * hb) % _P
    
    return commitment_value, blinding_factor


def pedersen_verify(
    commitment_value: int, value: int, blinding_factor: int
) -> bool:
    """Verify that a commitment opens to the claimed value.
    
    Recomputes g^value * h^blinding and checks equality.
    """
    gv = pow(_G, value, _P)
    hb = pow(_H, blinding_factor, _P)
    expected = (gv * hb) % _P
    return expected == commitment_value


def get_generators() -> Tuple[int, int]:
    """Return the group generators (g, h)."""
    return _G, _H


def get_prime() -> int:
    """Return the group prime."""
    return _P
