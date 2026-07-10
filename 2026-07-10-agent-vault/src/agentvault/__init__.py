"""AgentVault -- secret-scoped execution layer for AI agents.

Issues scoped, revocable, short-lived credentials (sessions) to agents instead of
handing them real secrets; filters egress to an allowlist; and records every secret
access in a tamper-evident audit trail.
"""
from __future__ import annotations

from agentvault.egress import EgressFilter, EgressRule
from agentvault.models import Scope, Secret, SecretKind, Session
from agentvault.vault import (
    AuditTrail,
    EgressDeniedError,
    ScopeDeniedError,
    SecretNotFoundError,
    SessionExpiredError,
    SessionNotFoundError,
    SessionRevokedError,
    UseLimitExceededError,
    Vault,
    VaultConfig,
    VaultError,
)

__all__ = [
    "AuditTrail",
    "EgressDeniedError",
    "EgressFilter",
    "EgressRule",
    "Scope",
    "ScopeDeniedError",
    "Secret",
    "SecretKind",
    "SecretNotFoundError",
    "Session",
    "SessionExpiredError",
    "SessionNotFoundError",
    "SessionRevokedError",
    "UseLimitExceededError",
    "Vault",
    "VaultConfig",
    "VaultError",
]
