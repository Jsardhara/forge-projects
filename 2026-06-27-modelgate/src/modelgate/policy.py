"""Policy engine — enforces access control rules and approval requirements."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from .models import AccessGrant, AccessStatus, ModelTier
from .store import ModelGateStore


@dataclass(frozen=True)
class AccessCheckResult:
    """Result of an access check."""

    allowed: bool
    reason: str
    grant: Optional[AccessGrant] = None


# Tier hierarchy: higher tiers require access to all lower tiers
TIER_HIERARCHY: dict[ModelTier, list[ModelTier]] = {
    ModelTier.PUBLIC: [],
    ModelTier.RESTRICTED: [ModelTier.PUBLIC],
    ModelTier.CLASSIFIED: [ModelTier.PUBLIC, ModelTier.RESTRICTED],
    ModelTier.GOVERNMENT_VETTED: [ModelTier.PUBLIC, ModelTier.RESTRICTED, ModelTier.CLASSIFIED],
}

# Approval requirements by tier
APPROVAL_REQUIRED: dict[ModelTier, bool] = {
    ModelTier.PUBLIC: False,
    ModelTier.RESTRICTED: True,
    ModelTier.CLASSIFIED: True,
    ModelTier.GOVERNMENT_VETTED: True,
}

# Justification requirements by tier
JUSTIFICATION_MIN_LENGTH: dict[ModelTier, int] = {
    ModelTier.PUBLIC: 0,
    ModelTier.RESTRICTED: 10,
    ModelTier.CLASSIFIED: 20,
    ModelTier.GOVERNMENT_VETTED: 30,
}


class PolicyEngine:
    """Enforces access control policies for ModelGate."""

    def __init__(self, store: ModelGateStore) -> None:
        self._store = store

    def check_access(
        self,
        employee_email: str,
        model_name: str,
    ) -> AccessCheckResult:
        """Check if an employee can access a specific model.

        Steps:
        1. Look up the model's tier
        2. Check if employee has an active grant for that tier
        3. Verify grant hasn't expired
        4. Return result with reason
        """
        model = self._store.get_model(model_name)
        if model is None:
            return AccessCheckResult(
                allowed=False,
                reason=f"Model '{model_name}' not found in registry",
            )

        tier = model.tier
        has_access = self._store.check_access(employee_email, tier)

        if not has_access:
            return AccessCheckResult(
                allowed=False,
                reason=f"No active {tier.value} access grant for {employee_email}",
            )

        # Verify the grant is not expired
        grants = self._store.list_grants(
            employee_email=employee_email,
            tier=tier,
            status=AccessStatus.ACTIVE,
        )
        if not grants:
            return AccessCheckResult(
                allowed=False,
                reason=f"No active grant found for {tier.value} tier",
            )

        grant = grants[0]
        if grant.expires_at and grant.expires_at < datetime.now(timezone.utc):
            return AccessCheckResult(
                allowed=False,
                reason=f"Access grant expired at {grant.expires_at.isoformat()}",
            )

        return AccessCheckResult(
            allowed=True,
            reason=f"Active {tier.value} access granted by {grant.approver}",
            grant=grant,
        )

    def validate_grant_request(
        self,
        employee_email: str,
        tier: ModelTier,
        justification: str,
        approver: str,
    ) -> Optional[str]:
        """Validate a grant request. Returns None if valid, or an error message."""
        # Employee must exist
        emp = self._store.get_employee(employee_email)
        if emp is None:
            return f"Employee '{employee_email}' not found"

        # Justification must meet minimum length
        min_len = JUSTIFICATION_MIN_LENGTH.get(tier, 0)
        if len(justification.strip()) < min_len:
            return f"Justification must be at least {min_len} characters for {tier.value} tier (got {len(justification.strip())})"

        # Approver is required for restricted+ tiers
        if APPROVAL_REQUIRED.get(tier, True) and not approver.strip():
            return f"Approver required for {tier.value} tier"

        # Check if already has access
        if self._store.check_access(employee_email, tier):
            return f"Employee already has active {tier.value} access"

        return None  # Valid

    def get_required_approvals(self, tier: ModelTier) -> list[str]:
        """Get the list of tiers that require approval for escalation."""
        if tier == ModelTier.PUBLIC:
            return []
        return [t.value for t in TIER_HIERARCHY[tier] if APPROVAL_REQUIRED.get(t, False)]

    def employee_tier_summary(self, employee_email: str) -> dict[ModelTier, bool]:
        """Get a summary of which tiers an employee has access to."""
        result = {}
        for tier in ModelTier:
            result[tier] = self._store.check_access(employee_email, tier)
        return result
