"""API Key Vault — Scoped, auditable key management for AI agents.

Keys are loaded from environment variables only (never hardcoded).
Each key has a scope defining which endpoints/models it can access.
"""

from __future__ import annotations

import os
import hashlib
import time
import json
import threading
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path


@dataclass(frozen=True)
class KeyScope:
    """Defines what an API key is allowed to access."""
    allowed_models: tuple[str, ...] = ()
    allowed_endpoints: tuple[str, ...] = ()
    max_requests_per_minute: int = 60
    max_tokens_per_day: int = 100_000

    def allows_model(self, model: str) -> bool:
        if not self.allowed_models:
            return True  # empty = allow all
        return model in self.allowed_models

    def allows_endpoint(self, endpoint: str) -> bool:
        if not self.allowed_endpoints:
            return True
        return endpoint in self.allowed_endpoints


@dataclass
class ApiKeyEntry:
    """A single API key with its scope and usage tracking."""
    name: str
    key_hash: str  # SHA-256 hash of the key (never store plaintext)
    scope: KeyScope
    created_at: float = field(default_factory=time.time)
    last_used: Optional[float] = None
    request_count: int = 0
    token_count: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def record_request(self, tokens: int = 0) -> None:
        with self._lock:
            self.last_used = time.time()
            self.request_count += 1
            self.token_count += tokens

    def masked_key(self) -> str:
        """Return a masked version of the hash for display."""
        return self.key_hash[:8] + "..." + self.key_hash[-4:]


class VaultError(Exception):
    """Raised when vault operations fail."""
    pass


class PermissionDenied(VaultError):
    """Raised when a key is used outside its scope."""
    pass


class ApiKeyVault:
    """Manages API keys with scoped permissions and audit logging.

    Keys are loaded from environment variables. The vault never stores
    plaintext keys — only SHA-256 hashes for verification.

    Usage:
        vault = ApiKeyVault()
        vault.load_from_env("OPENAI_API_KEY", scope=KeyScope(allowed_models=("gpt-4",)))
        vault.check_permission("openai", "gpt-4", "/v1/chat/completions")
    """

    def __init__(self) -> None:
        self._entries: dict[str, ApiKeyEntry] = {}
        self._audit_log: list[dict] = []
        self._lock = threading.Lock()

    def load_from_env(
        self,
        env_var: str,
        name: str | None = None,
        scope: KeyScope | None = None,
    ) -> str:
        """Load an API key from an environment variable.

        Args:
            env_var: Name of the environment variable containing the key.
            name: Human-readable name for this key (defaults to env_var).
            scope: Permission scope for this key.

        Returns:
            The key name for reference.

        Raises:
            VaultError: If the environment variable is not set.
        """
        key = os.environ.get(env_var)
        if not key:
            raise VaultError(
                f"Environment variable '{env_var}' is not set. "
                f"Set it before loading the vault."
            )

        key_name = name or env_var.lower()
        key_hash = hashlib.sha256(key.encode()).hexdigest()

        entry = ApiKeyEntry(
            name=key_name,
            key_hash=key_hash,
            scope=scope or KeyScope(),
        )

        with self._lock:
            self._entries[key_name] = entry
        self._audit("key_loaded", key_name=key_name, env_var=env_var)

        return key_name

    def check_permission(
        self,
        key_name: str,
        model: str = "",
        endpoint: str = "",
        tokens: int = 0,
    ) -> bool:
        """Check if a key has permission for the given action.

        Args:
            key_name: The key identifier.
            model: Model name being accessed.
            endpoint: API endpoint being called.
            tokens: Estimated token count for this request.

        Returns:
            True if permission is granted.

        Raises:
            PermissionDenied: If the action is outside the key's scope.
            VaultError: If the key is not found.
        """
        entry = self._entries.get(key_name)
        if not entry:
            raise VaultError(f"Key '{key_name}' not found in vault")

        if model and not entry.scope.allows_model(model):
            self._audit("permission_denied", key_name=key_name, model=model, reason="model_not_allowed")
            raise PermissionDenied(
                f"Key '{key_name}' is not allowed to access model '{model}'. "
                f"Allowed: {entry.scope.allowed_models or 'all'}"
            )

        if endpoint and not entry.scope.allows_endpoint(endpoint):
            self._audit("permission_denied", key_name=key_name, endpoint=endpoint, reason="endpoint_not_allowed")
            raise PermissionDenied(
                f"Key '{key_name}' is not allowed to access endpoint '{endpoint}'. "
                f"Allowed: {entry.scope.allowed_endpoints or 'all'}"
            )

        entry.record_request(tokens)
        self._audit("permission_granted", key_name=key_name, model=model, endpoint=endpoint, tokens=tokens)
        return True

    def get_usage(self, key_name: str) -> dict:
        """Get usage statistics for a key."""
        entry = self._entries.get(key_name)
        if not entry:
            raise VaultError(f"Key '{key_name}' not found in vault")
        return {
            "name": entry.name,
            "request_count": entry.request_count,
            "token_count": entry.token_count,
            "last_used": entry.last_used,
            "created_at": entry.created_at,
        }

    def get_all_usage(self) -> list[dict]:
        """Get usage statistics for all keys."""
        return [self.get_usage(name) for name in self._entries]

    def get_audit_log(self) -> list[dict]:
        """Return the full audit log."""
        with self._lock:
            return list(self._audit_log)

    def _audit(self, event: str, **kwargs) -> None:
        """Record an audit event."""
        with self._lock:
            self._audit_log.append({
                "event": event,
                "timestamp": time.time(),
                **kwargs,
            })

    @property
    def key_count(self) -> int:
        return len(self._entries)
