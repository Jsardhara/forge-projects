"""posture — compose this repo's read-only verifiers into one exit code."""

from .models import (  # noqa: F401
    CLEAN,
    ERROR,
    FINDINGS,
    UNMEASURABLE,
    VerifierResult,
)
from .specs import DEFAULT_SPECS, VerifierSpec  # noqa: F401

__version__ = "1.0.0"
__all__ = [
    "CLEAN",
    "ERROR",
    "FINDINGS",
    "UNMEASURABLE",
    "VerifierResult",
    "DEFAULT_SPECS",
    "VerifierSpec",
    "__version__",
]
