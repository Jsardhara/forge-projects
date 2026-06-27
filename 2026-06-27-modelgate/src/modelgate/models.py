"""Data models for ModelGate — tiers, employees, access grants, audit entries."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


class ModelTier(enum.Enum):
    """Classification tiers for AI model access."""

    PUBLIC = "public"
    RESTRICTED = "restricted"
    CLASSIFIED = "classified"
    GOVERNMENT_VETTED = "government_vetted"


class AccessStatus(enum.Enum):
    """Status of an access grant."""

    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    PENDING = "pending"
    DENIED = "denied"


class AccessRequestStatus(enum.Enum):
    """Status of an access request."""

    OPEN = "open"
    APPROVED = "approved"
    DENIED = "denied"


@dataclass(frozen=True)
class Model:
    """An AI model with its tier classification."""

    name: str
    provider: str
    tier: ModelTier
    description: str = ""


@dataclass(frozen=True)
class Employee:
    """An employee who may be granted access to AI models."""

    email: str
    name: str
    department: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class AccessGrant:
    """A grant of access from an employee to a model tier."""

    vid: str  # avoid shadowing builtin id
    employee_email: str
    tier: ModelTier
    justification: str
    approver: str
    granted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    status: AccessStatus = AccessStatus.ACTIVE


@dataclass(frozen=True)
class AccessRequest:
    """A request from an employee to access a model tier."""

    vid: str
    employee_email: str
    tier: ModelTier
    justification: str
    requested_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: AccessRequestStatus = AccessRequestStatus.OPEN
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    denial_reason: Optional[str] = None


@dataclass(frozen=True)
class AuditEntry:
    """Immutable audit log entry recording a model access event."""

    vid: str
    employee_email: str
    model_name: str
    purpose: str
    accessed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tier_at_access: ModelTier = ModelTier.PUBLIC


@dataclass(frozen=True)
class ComplianceReport:
    """A generated compliance report covering a date range."""

    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    since: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    until: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    total_accesses: int = 0
    unique_employees: int = 0
    classified_accesses: int = 0
    government_vetted_accesses: int = 0
    expired_grants: int = 0
    revoked_grants: int = 0
    pending_requests: int = 0
