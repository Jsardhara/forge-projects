"""AgentIAM — AI Agent Identity & Access Management.

A focused Python library for managing AI agent identities,
short-lived credentials, policy-based access control, and audit trails.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class AgentStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    REVOKED = "revoked"


class CredentialStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"


@dataclass
class AgentIdentity:
    """Represents a registered AI agent with a unique, verifiable identity."""

    agent_id: str
    name: str
    owner: str
    description: str = ""
    code_hash: str = ""          # SHA-256 of agent code for integrity binding
    model_id: str = ""           # e.g. "openai/gpt-4o"
    scopes: list[str] = field(default_factory=list)
    status: AgentStatus = AgentStatus.ACTIVE
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_active(self) -> bool:
        return self.status == AgentStatus.ACTIVE

    def fingerprint(self) -> str:
        """Return a short fingerprint of this identity for logging."""
        raw = f"{self.agent_id}:{self.name}:{self.code_hash}"
        return hashlib.sha256(raw.encode()).hexdigest()[:12]


@dataclass
class Credential:
    """A short-lived, scope-bound credential issued to an agent."""

    credential_id: str
    agent_id: str
    token: str
    scopes: list[str]
    issued_at: datetime
    expires_at: datetime
    status: CredentialStatus = CredentialStatus.ACTIVE
    issued_by: str = "agentiam"

    @property
    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) >= self.expires_at

    @property
    def is_valid(self) -> bool:
        return self.status == CredentialStatus.ACTIVE and not self.is_expired

    def time_remaining(self) -> float:
        """Seconds remaining until expiry. Negative if expired."""
        delta = self.expires_at - datetime.now(timezone.utc)
        return delta.total_seconds()


@dataclass
class AccessPolicy:
    """A policy that defines what an agent can do."""

    policy_id: str
    name: str
    description: str = ""
    allowed_scopes: list[str] = field(default_factory=list)
    denied_scopes: list[str] = field(default_factory=list)
    max_chain_depth: int = 3          # max delegation depth
    require_human_approval: bool = False
    rate_limit_per_minute: int = 60
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class AuditEvent:
    """A single auditable action performed by or about an agent."""

    event_id: str
    agent_id: str
    action: str
    resource: str
    result: str                       # "allow" | "deny" | "error"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    details: dict[str, Any] = field(default_factory=dict)
    credential_id: str = ""


# ---------------------------------------------------------------------------
# Identity Registry
# ---------------------------------------------------------------------------

class IdentityRegistry:
    """In-memory registry for agent identities with full CRUD."""

    def __init__(self) -> None:
        self._agents: dict[str, AgentIdentity] = {}

    def register(
        self,
        name: str,
        owner: str,
        description: str = "",
        code_hash: str = "",
        model_id: str = "",
        scopes: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AgentIdentity:
        if not name:
            raise ValueError("Agent name is required")
        if not owner:
            raise ValueError("Agent owner is required")

        agent_id = f"agent-{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)
        agent = AgentIdentity(
            agent_id=agent_id,
            name=name,
            owner=owner,
            description=description,
            code_hash=code_hash,
            model_id=model_id,
            scopes=scopes or [],
            status=AgentStatus.ACTIVE,
            created_at=now,
            updated_at=now,
            metadata=metadata or {},
        )
        self._agents[agent_id] = agent
        return agent

    def get(self, agent_id: str) -> AgentIdentity | None:
        return self._agents.get(agent_id)

    def list_agents(self, status: AgentStatus | None = None) -> list[AgentIdentity]:
        agents = list(self._agents.values())
        if status is not None:
            agents = [a for a in agents if a.status == status]
        return agents

    def update_status(self, agent_id: str, status: AgentStatus) -> AgentIdentity:
        agent = self._agents.get(agent_id)
        if agent is None:
            raise KeyError(f"Agent not found: {agent_id}")
        agent.status = status
        agent.updated_at = datetime.now(timezone.utc)
        return agent

    def suspend(self, agent_id: str) -> AgentIdentity:
        return self.update_status(agent_id, AgentStatus.SUSPENDED)

    def revoke(self, agent_id: str) -> AgentIdentity:
        return self.update_status(agent_id, AgentStatus.REVOKED)

    def update_code_hash(self, agent_id: str, code_hash: str) -> AgentIdentity:
        agent = self._agents.get(agent_id)
        if agent is None:
            raise KeyError(f"Agent not found: {agent_id}")
        agent.code_hash = code_hash
        agent.updated_at = datetime.now(timezone.utc)
        return agent

    def count(self) -> int:
        return len(self._agents)


# ---------------------------------------------------------------------------
# Credential Manager
# ---------------------------------------------------------------------------

class CredentialManager:
    """Issues, validates, rotates, and revokes short-lived credentials."""

    def __init__(self, registry: IdentityRegistry, default_ttl: int = 3600) -> None:
        self._registry = registry
        self._default_ttl = default_ttl
        self._credentials: dict[str, Credential] = {}

    def issue(
        self,
        agent_id: str,
        scopes: list[str] | None = None,
        ttl: int | None = None,
        issued_by: str = "agentiam",
    ) -> Credential:
        agent = self._registry.get(agent_id)
        if agent is None:
            raise KeyError(f"Agent not found: {agent_id}")
        if not agent.is_active:
            raise PermissionError(f"Agent {agent_id} is {agent.status.value}, cannot issue credential")

        cred_id = f"cred-{uuid.uuid4().hex[:12]}"
        token = secrets.token_urlsafe(48)
        effective_ttl = ttl if ttl is not None else self._default_ttl
        now = datetime.now(timezone.utc)

        cred = Credential(
            credential_id=cred_id,
            agent_id=agent_id,
            token=token,
            scopes=scopes or agent.scopes,
            issued_at=now,
            expires_at=datetime.fromtimestamp(now.timestamp() + effective_ttl, tz=timezone.utc),
            status=CredentialStatus.ACTIVE,
            issued_by=issued_by,
        )
        self._credentials[cred_id] = cred
        return cred

    def validate(self, token: str) -> Credential:
        cred = self._find_by_token(token)
        if cred is None:
            raise PermissionError("Invalid credential token")
        if cred.is_expired:
            cred.status = CredentialStatus.EXPIRED
            raise PermissionError(f"Credential {cred.credential_id} has expired")
        if cred.status == CredentialStatus.REVOKED:
            raise PermissionError(f"Credential {cred.credential_id} has been revoked")
        agent = self._registry.get(cred.agent_id)
        if agent is None or not agent.is_active:
            raise PermissionError(f"Agent {cred.agent_id} is not active")
        return cred

    def revoke(self, credential_id: str) -> Credential:
        cred = self._credentials.get(credential_id)
        if cred is None:
            raise KeyError(f"Credential not found: {credential_id}")
        cred.status = CredentialStatus.REVOKED
        return cred

    def rotate(self, credential_id: str, ttl: int | None = None) -> Credential:
        old = self._credentials.get(credential_id)
        if old is None:
            raise KeyError(f"Credential not found: {credential_id}")
        # Revoke old
        old.status = CredentialStatus.REVOKED
        # Issue new
        return self.issue(
            agent_id=old.agent_id,
            scopes=old.scopes,
            ttl=ttl,
            issued_by="agentiam-rotate",
        )

    def list_for_agent(self, agent_id: str) -> list[Credential]:
        return [c for c in self._credentials.values() if c.agent_id == agent_id]

    def _find_by_token(self, token: str) -> Credential | None:
        for cred in self._credentials.values():
            if hmac.compare_digest(cred.token, token):
                return cred
        return None

    def count(self) -> int:
        return len(self._credentials)


# ---------------------------------------------------------------------------
# Policy Engine
# ---------------------------------------------------------------------------

class PolicyEngine:
    """Evaluates access requests against registered policies."""

    def __init__(self) -> None:
        self._policies: dict[str, AccessPolicy] = {}

    def add_policy(self, policy: AccessPolicy) -> None:
        self._policies[policy.policy_id] = policy

    def create_policy(
        self,
        name: str,
        description: str = "",
        allowed_scopes: list[str] | None = None,
        denied_scopes: list[str] | None = None,
        max_chain_depth: int = 3,
        require_human_approval: bool = False,
        rate_limit_per_minute: int = 60,
    ) -> AccessPolicy:
        pid = f"pol-{uuid.uuid4().hex[:8]}"
        pol = AccessPolicy(
            policy_id=pid,
            name=name,
            description=description,
            allowed_scopes=allowed_scopes or [],
            denied_scopes=denied_scopes or [],
            max_chain_depth=max_chain_depth,
            require_human_approval=require_human_approval,
            rate_limit_per_minute=rate_limit_per_minute,
        )
        self._policies[pid] = pol
        return pol

    def evaluate(
        self,
        policy_id: str,
        requested_scopes: list[str],
        chain_depth: int = 0,
    ) -> tuple[bool, str]:
        """Return (allowed, reason)."""
        policy = self._policies.get(policy_id)
        if policy is None:
            return False, f"Policy not found: {policy_id}"

        # Check chain depth
        if chain_depth > policy.max_chain_depth:
            return False, f"Chain depth {chain_depth} exceeds max {policy.max_chain_depth}"

        # Check denied scopes first
        for scope in requested_scopes:
            if scope in policy.denied_scopes:
                return False, f"Scope '{scope}' is explicitly denied"

        # Check allowed scopes (empty list = allow all)
        if policy.allowed_scopes:
            for scope in requested_scopes:
                if scope not in policy.allowed_scopes:
                    return False, f"Scope '{scope}' not in allowed list"

        if policy.require_human_approval:
            return False, "Human approval required for this policy"

        return True, "Access granted"

    def get_policy(self, policy_id: str) -> AccessPolicy | None:
        return self._policies.get(policy_id)

    def list_policies(self) -> list[AccessPolicy]:
        return list(self._policies.values())


# ---------------------------------------------------------------------------
# Audit Log
# ---------------------------------------------------------------------------

class AuditLog:
    """Append-only audit log for all agent actions."""

    def __init__(self) -> None:
        self._events: list[AuditEvent] = []

    def record(
        self,
        agent_id: str,
        action: str,
        resource: str,
        result: str,
        details: dict[str, Any] | None = None,
        credential_id: str = "",
    ) -> AuditEvent:
        event = AuditEvent(
            event_id=f"evt-{uuid.uuid4().hex[:12]}",
            agent_id=agent_id,
            action=action,
            resource=resource,
            result=result,
            details=details or {},
            credential_id=credential_id,
        )
        self._events.append(event)
        return event

    def for_agent(self, agent_id: str) -> list[AuditEvent]:
        return [e for e in self._events if e.agent_id == agent_id]

    def for_action(self, action: str) -> list[AuditEvent]:
        return [e for e in self._events if e.action == action]

    def since(self, ts: datetime) -> list[AuditEvent]:
        return [e for e in self._events if e.timestamp >= ts]

    def all(self) -> list[AuditEvent]:
        return list(self._events)

    def count(self) -> int:
        return len(self._events)

    def export_json(self) -> str:
        events = []
        for e in self._events:
            events.append({
                "event_id": e.event_id,
                "agent_id": e.agent_id,
                "action": e.action,
                "resource": e.resource,
                "result": e.result,
                "timestamp": e.timestamp.isoformat(),
                "credential_id": e.credential_id,
                "details": e.details,
            })
        return json.dumps(events, indent=2)


# ---------------------------------------------------------------------------
# AgentIAM — Main Facade
# ---------------------------------------------------------------------------

class AgentIAM:
    """Main entry point — ties together identity, credentials, policy, and audit."""

    def __init__(self, default_credential_ttl: int = 3600) -> None:
        self.registry = IdentityRegistry()
        self.credentials = CredentialManager(self.registry, default_credential_ttl)
        self.policies = PolicyEngine()
        self.audit = AuditLog()

    def register_agent(self, **kwargs: Any) -> AgentIdentity:
        agent = self.registry.register(**kwargs)
        self.audit.record(agent.agent_id, "register", "identity", "allow")
        return agent

    def issue_credential(self, agent_id: str, **kwargs: Any) -> Credential:
        cred = self.credentials.issue(agent_id, **kwargs)
        self.audit.record(agent_id, "issue_credential", f"credential:{cred.credential_id}", "allow")
        return cred

    def validate_credential(self, token: str) -> Credential:
        try:
            cred = self.credentials.validate(token)
            self.audit.record(
                cred.agent_id, "validate", f"credential:{cred.credential_id}", "allow",
                credential_id=cred.credential_id,
            )
            return cred
        except PermissionError as exc:
            self.audit.record("unknown", "validate", "credential", "deny", details={"error": str(exc)})
            raise

    def check_access(
        self,
        token: str,
        requested_scopes: list[str],
        policy_id: str,
        chain_depth: int = 0,
    ) -> tuple[bool, str]:
        """Full access check: validate credential + evaluate policy."""
        try:
            cred = self.validate_credential(token)
        except PermissionError as exc:
            return False, str(exc)

        allowed, reason = self.policies.evaluate(policy_id, requested_scopes, chain_depth)
        result = "allow" if allowed else "deny"
        self.audit.record(
            cred.agent_id, "check_access", f"policy:{policy_id}", result,
            details={"scopes": requested_scopes, "reason": reason, "chain_depth": chain_depth},
            credential_id=cred.credential_id,
        )
        return allowed, reason

    def revoke_agent(self, agent_id: str) -> AgentIdentity:
        agent = self.registry.revoke(agent_id)
        # Also revoke all active credentials
        for cred in self.credentials.list_for_agent(agent_id):
            if cred.is_valid:
                self.credentials.revoke(cred.credential_id)
        self.audit.record(agent_id, "revoke", "identity", "allow")
        return agent

    def suspend_agent(self, agent_id: str) -> AgentIdentity:
        agent = self.registry.suspend(agent_id)
        self.audit.record(agent_id, "suspend", "identity", "allow")
        return agent
