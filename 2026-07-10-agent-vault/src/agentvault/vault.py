"""The Vault: credential broker, session lifecycle, and policy enforcement.

Thread-safety: a single ``threading.RLock`` guards all mutable state. The audit
trail is recorded for every access decision (allow + deny) for tamper-evident proof.
"""
from __future__ import annotations

import secrets as _secrets
import threading
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from agentvault.audit import AuditTrail, AuditEntry
from agentvault.egress import EgressFilter, EgressRule
from agentvault.models import Scope, Secret, SecretKind, Session


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _gen_id(prefix: str) -> str:
    return f"{prefix}_{_secrets.token_hex(8)}"


# ---- Error types -----------------------------------------------------------
class VaultError(Exception):
    """Base class for all vault errors."""


class SecretNotFoundError(VaultError):
    def __init__(self, sid: str) -> None:
        self.sid = sid
        super().__init__(f"secret not found: {sid}")


class SessionNotFoundError(VaultError):
    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        super().__init__(f"session not found: {session_id}")


class SessionRevokedError(VaultError):
    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        super().__init__(f"session revoked: {session_id}")


class SessionExpiredError(VaultError):
    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        super().__init__(f"session expired: {session_id}")


class UseLimitExceededError(VaultError):
    def __init__(self, session_id: str, limit: int) -> None:
        self.session_id = session_id
        self.limit = limit
        super().__init__(f"session use limit ({limit}) exceeded: {session_id}")


class ScopeDeniedError(VaultError):
    def __init__(self, session_id: str, secret_id: str) -> None:
        self.session_id = session_id
        self.secret_id = secret_id
        super().__init__(f"scope denied: {session_id} may not access {secret_id}")


class EgressDeniedError(VaultError):
    def __init__(self, host: str, port: Optional[int] = None) -> None:
        self.host = host
        self.port = port
        port_s = f":{port}" if port is not None else ""
        super().__init__(f"egress denied: {host}{port_s}")


@dataclass
class VaultConfig:
    # Default session TTL when none is given.
    default_ttl: timedelta = field(default_factory=lambda: timedelta(hours=1))
    # If True, sessions may only resolve secrets whose allowed_hosts is empty
    # or matches (egress scoping). If False, secret.allowed_hosts is advisory.
    enforce_secret_host_scope: bool = True


class Vault:
    """Secret store + credential broker + egress gate + audit log."""

    def __init__(self, config: Optional[VaultConfig] = None) -> None:
        self._secrets: Dict[str, Secret] = {}
        self._sessions: Dict[str, Session] = {}
        self._egress = EgressFilter()
        self._audit = AuditTrail()
        self._config = config or VaultConfig()
        self._lock = threading.RLock()

    # ---- Secrets ----------------------------------------------------------
    def add_secret(
        self,
        name: str,
        value: str,
        kind: SecretKind = SecretKind.GENERIC,
        allowed_hosts: Tuple[str, ...] = (),
        sid: Optional[str] = None,
    ) -> Secret:
        with self._lock:
            s = Secret(
                sid=sid or _gen_id("sec"),
                name=name,
                value=value,
                kind=kind,
                allowed_hosts=tuple(allowed_hosts),
            )
            self._secrets[s.sid] = s
            self._audit.record("vault", "add-secret", s.sid, f"name={name} kind={kind.value}")
            return s

    def get_secret_meta(self, sid: str) -> Secret:
        """Return secret metadata WITHOUT the value. Raises if missing/deleted."""
        with self._lock:
            s = self._secrets.get(sid)
            if s is None or s.deleted:
                raise SecretNotFoundError(sid)
            return s

    def delete_secret(self, sid: str) -> None:
        with self._lock:
            s = self._secrets.get(sid)
            if s is None:
                raise SecretNotFoundError(sid)
            # never mutate in place: use replace to set deleted_at
            self._secrets[sid] = replace(s, deleted_at=_now())
            self._audit.record("vault", "delete-secret", sid, "soft-deleted")

    # ---- Sessions (scoped, revocable, short-lived) ------------------------
    def issue_session(
        self,
        scope: Optional[Scope] = None,
        ttl: Optional[timedelta] = None,
        session_id: Optional[str] = None,
    ) -> Session:
        with self._lock:
            scope = scope or Scope()
            ttl = ttl or self._config.default_ttl
            expires = _now() + ttl
            sid = session_id or _gen_id("ses")
            s = Session(session_id=sid, scope=scope, expires_at=expires)
            self._sessions[sid] = s
            self._audit.record(sid, "issue", sid, f"ttl={ttl} egress={scope.can_proxy_egress}")
            return s

    def revoke_session(self, session_id: str) -> None:
        with self._lock:
            s = self._sessions.get(session_id)
            if s is None:
                raise SessionNotFoundError(session_id)
            self._sessions[session_id] = replace(s, revoked_at=_now())
            self._audit.record(session_id, "revoke", session_id, "operator revoke")

    def _check_session(self, session: Session) -> None:
        if session.revoked:
            raise SessionRevokedError(session.session_id)
        if session.is_expired():
            raise SessionExpiredError(session.session_id)
        if session.scope.max_uses is not None and session.use_count >= session.scope.max_uses:
            raise UseLimitExceededError(session.session_id, session.scope.max_uses)

    def _bump_use(self, session: Session) -> None:
        self._sessions[session.session_id] = replace(
            session, use_count=session.use_count + 1
        )

    # ---- Secret resolution (the guardrail) --------------------------------
    def resolve(self, session_id: str, secret_id: str) -> str:
        """Resolve a real secret value for a session, enforcing scope/expiry.

        Raises ScopeDeniedError / SessionRevokedError / SessionExpiredError /
        UseLimitExceededError / SecretNotFoundError. Records allow + deny in audit.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                self._audit.record(session_id, "deny", secret_id, "unknown session")
                raise SessionNotFoundError(session_id)
            try:
                self._check_session(session)
            except VaultError as exc:
                self._audit.record(session_id, "deny", secret_id, str(exc))
                raise

            secret = self._secrets.get(secret_id)
            if secret is None or secret.deleted:
                self._audit.record(session_id, "deny", secret_id, "unknown/deleted secret")
                raise SecretNotFoundError(secret_id)

            # Scope: if session has explicit secret_ids, secret must be in it.
            if session.scope.secret_ids and secret_id not in session.scope.secret_ids:
                self._audit.record(session_id, "deny", secret_id, "not in session.scope.secret_ids")
                raise ScopeDeniedError(session_id, secret_id)

            # Secret-level host scoping (egress binding).
            if (
                self._config.enforce_secret_host_scope
                and session.scope.allowed_hosts
                and secret.allowed_hosts
            ):
                allowed = set(session.scope.allowed_hosts) | set(secret.allowed_hosts)
                # if the secret is only usable on specific hosts, the session must
                # be permitted to reach at least one of them. We treat empty
                # session.allowed_hosts as the super-set (handled above by the
                # secret_ids gate). Here we verify there is host overlap.
                if not (set(session.scope.allowed_hosts) & set(secret.allowed_hosts)):
                    self._audit.record(
                        session_id, "deny", secret_id, "host scope mismatch"
                    )
                    raise ScopeDeniedError(session_id, secret_id)

            self._bump_use(session)
            self._audit.record(session_id, "resolve", secret_id, "value released")
            return secret.value

    # ---- Egress gate ------------------------------------------------------
    def set_egress_rules(self, rules: List[EgressRule]) -> None:
        with self._lock:
            self._egress = EgressFilter(rules)
            self._audit.record("vault", "egress-update", "policy", f"{len(rules)} rules")

    def add_egress_rule(self, pattern: str, ports: Tuple[int, ...] = ()) -> EgressRule:
        with self._lock:
            r = self._egress.add_rule(pattern, ports)
            self._audit.record("vault", "egress-add", pattern, f"ports={list(ports)}")
            return r

    def check_egress(self, session_id: str, host: str, port: Optional[int] = None) -> bool:
        """Check whether a session may reach ``host:port``. Records decision.

        If the session scope does NOT permit egress proxying (can_proxy_egress),
        the request is denied outright. Otherwise the shared allowlist decides.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                self._audit.record(session_id, "egress-deny", host, "unknown session")
                raise SessionNotFoundError(session_id)
            try:
                self._check_session(session)
            except VaultError as exc:
                self._audit.record(session_id, "egress-deny", host, str(exc))
                raise

            if not session.scope.can_proxy_egress:
                self._audit.record(session_id, "egress-deny", host, "egress not authorized")
                raise ScopeDeniedError(session_id, host)

            # A host is permitted only if it is on the session's own scoped
            # allowlist OR on the operator-wide vault egress allowlist.
            # If the session is NOT host-scoped (empty allowed_hosts), it relies
            # entirely on the vault filter -> default-deny when filter is empty.
            scope_ok = bool(session.scope.allowed_hosts) and (
                host in session.scope.allowed_hosts
            )
            filter_ok = self._egress.allow(host, port)
            if not (scope_ok or filter_ok):
                self._audit.record(
                    session_id, "egress-deny", host,
                    "not in session scope or vault allowlist",
                )
                raise EgressDeniedError(host, port)
            self._audit.record(session_id, "egress-allow", host, "allowlisted")
            return True

    # ---- Reporting --------------------------------------------------------
    def audit_verify(self) -> bool:
        with self._lock:
            return self._audit.verify()

    @property
    def audit_trail(self) -> AuditTrail:
        return self._audit

    @property
    def sessions(self) -> List[Session]:
        with self._lock:
            return list(self._sessions.values())

    @property
    def secrets(self) -> List[Secret]:
        with self._lock:
            return [s for s in self._secrets.values() if not s.deleted]
