"""Core data models for AgentVault.

Frozen dataclasses are used for immutability (no accidental in-place mutation of
security-critical state). Mutating operations go through ``dataclasses.replace``.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Tuple


def _now() -> datetime:
    """Timezone-aware UTC timestamp. Never use naive utcnow()."""
    return datetime.now(timezone.utc)


class SecretKind(str, Enum):
    API_KEY = "api_key"
    TOKEN = "token"
    PASSWORD = "password"
    CERT = "cert"
    GENERIC = "generic"


@dataclass(frozen=True)
class Secret:
    """A real secret stored in the vault. The ``value`` is never handed to an agent
    raw; it is only resolved at the moment of use, after scope/expiry checks pass."""

    sid: str
    name: str
    value: str
    kind: SecretKind = SecretKind.GENERIC
    # Hosts this secret is permitted to be used against (egress scoping). Empty = any.
    allowed_hosts: Tuple[str, ...] = ()
    created_at: datetime = field(default_factory=_now)
    deleted_at: Optional[datetime] = None

    @property
    def deleted(self) -> bool:
        return self.deleted_at is not None


@dataclass(frozen=True)
class Scope:
    """What a session (token) is permitted to do."""

    # Secret ids this token may resolve. Empty tuple = all secrets granted to scope.
    secret_ids: Tuple[str, ...] = ()
    # Egress hosts this token is allowed to reach (allowlist it may use).
    allowed_hosts: Tuple[str, ...] = ()
    # Whether egress proxying is authorized at all for this token.
    can_proxy_egress: bool = False
    # Maximum number of secret resolutions before the token burns out. None = unlimited.
    max_uses: Optional[int] = None


@dataclass(frozen=True)
class Session:
    """A scoped, revocable, short-lived credential handed to an agent."""

    session_id: str
    scope: Scope = field(default_factory=Scope)
    issued_at: datetime = field(default_factory=_now)
    expires_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    use_count: int = 0

    @property
    def revoked(self) -> bool:
        return self.revoked_at is not None

    def is_expired(self, when: Optional[datetime] = None) -> bool:
        if self.expires_at is None:
            return False
        when = when or _now()
        return when >= self.expires_at
