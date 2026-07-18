"""Data models for LicGuard.

All records are immutable (frozen dataclasses) so a computed verdict can never be
silently mutated after the fact.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Set

# Permission / condition / limitation vocabulary (shared across the engine)
PERM_COMMERCIAL = "commercial-use"
PERM_REDISTRIBUTE = "redistribute"
PERM_FINETUNE = "finetune"
PERM_HOSTING = "hosting"

LIM_COMMERCIAL = "no-commercial"
LIM_REDISTRIBUTE = "no-redistribute"
LIM_FINETUNE = "no-finetune"

COND_ACCEPTABLE_USE = "acceptable-use-policy"
COND_LICENSE_THRESHOLD = "license-threshold"


@dataclass(frozen=True)
class License:
    """A known open-weight model license / terms-of-use record."""

    key: str                       # short id, e.g. "llama3.1-community"
    name: str                      # human-readable name
    spdx: Optional[str]            # SPDX id if a standard license, else None
    permissions: Set[str] = field(default_factory=set)
    conditions: Set[str] = field(default_factory=set)
    limitations: Set[str] = field(default_factory=set)
    # specific carve-outs
    max_monthly_users: Optional[int] = None   # commercial threshold before extra terms
    prohibited_uses: Set[str] = field(default_factory=set)  # AUP / banned domains
    notes: str = ""


@dataclass(frozen=True)
class ModelLicense:
    """Binds a model id to its license record and alias tokens for matching."""

    model_id: str                  # canonical model id, e.g. "llama-3.1-8b"
    aliases: Set[str] = field(default_factory=set)  # tokens used for fuzzy match
    license: License = None        # None => license not yet published (NEEDS_REVIEW)
    notes: str = ""


@dataclass(frozen=True)
class DeploymentContext:
    """What the operator intends to do with the model."""

    commercial: bool = False
    redistribute: bool = False
    finetune: bool = False
    hosting: bool = False          # offering inference to third parties
    monthly_active_users: Optional[int] = None
    use_case: str = ""             # free-text; scanned for prohibited domains


@dataclass(frozen=True)
class Verdict:
    status: str                    # COMPLIANT | NEEDS_REVIEW | NON_COMPLIANT
    model_id: str
    license_key: Optional[str]
    reasons: List[str] = field(default_factory=list)
    confidence: float = 1.0

    def merge(self, other: "Verdict") -> "Verdict":
        """Combine reason lists; downgrade status to the strictest of the two."""
        order = {"COMPLIANT": 0, "NEEDS_REVIEW": 1, "NON_COMPLIANT": 2}
        combined_status = self.status
        if order.get(other.status, 1) > order.get(self.status, 0):
            combined_status = other.status
        return Verdict(
            status=combined_status,
            model_id=self.model_id,
            license_key=self.license_key,
            reasons=self.reasons + other.reasons,
            confidence=min(self.confidence, other.confidence),
        )
