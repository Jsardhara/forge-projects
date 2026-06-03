"""Sandbox — Main orchestrator that ties all subsystems together.

Combines the API key vault, network egress controller, filesystem sandbox,
and audit logger into a single unified interface for securing AI agents.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

from .vault import ApiKeyVault, KeyScope, VaultError, PermissionDenied
from .egress import NetworkEgressController, EgressEvent
from .fsandbox import FilesystemSandbox, FileAccessEvent
from .audit import AuditLogger, AuditEntry


@dataclass
class SandboxConfig:
    """Configuration for the AI Agent Sandbox."""
    agent_id: str = "default"
    allowed_dirs: list[str] = field(default_factory=list)
    allowed_domains: list[str] = field(default_factory=list)
    default_deny_network: bool = True
    allow_tmp: bool = True


class Sandbox:
    """Unified AI Agent Security Sandbox.

    Combines all security subsystems into a single interface:
    - API key vault with scoped permissions
    - Network egress control with domain allowlist
    - Filesystem access monitoring
    - Centralized audit logging
    - Kill switch for emergency stop

    Usage:
        sb = Sandbox(SandboxConfig(
            agent_id="claude-code-1",
            allowed_dirs=["/home/user/projects/myapp"],
            allowed_domains=["api.openai.com", "api.anthropic.com"],
        ))

        # Check network access
        if sb.check_network("https://api.openai.com/v1/chat"):
            # proceed

        # Check filesystem access
        if sb.check_file("/home/user/projects/myapp/src/main.py", "read"):
            # proceed

        # Check API key permission
        sb.check_key("openai", model="gpt-4")

        # Emergency stop
        sb.kill()

        # Review audit trail
        print(sb.audit_summary())
    """

    def __init__(self, config: SandboxConfig | None = None) -> None:
        self._config = config or SandboxConfig()
        self._agent_id = self._config.agent_id

        # Initialize subsystems
        self.vault = ApiKeyVault()
        self.network = NetworkEgressController(default_deny=self._config.default_deny_network)
        self.fs = FilesystemSandbox(
            agent_id=self._agent_id,
            allowed_dirs=self._config.allowed_dirs,
            allow_tmp=self._config.allow_tmp,
        )
        self.audit = AuditLogger(agent_id=self._agent_id)

        # Configure network allowlist
        for domain in self._config.allowed_domains:
            self.network.allow_domain(domain)

    def load_key(
        self,
        env_var: str,
        name: str | None = None,
        scope: KeyScope | None = None,
    ) -> str:
        """Load an API key from an environment variable."""
        key_name = self.vault.load_from_env(env_var, name=name, scope=scope)
        self.audit.log("key_access", f"load_key:{key_name}", True, detail=f"env_var={env_var}")
        return key_name

    def check_key(self, key_name: str, model: str = "", endpoint: str = "") -> bool:
        """Check if an API key has permission for the given action."""
        try:
            result = self.vault.check_permission(key_name, model=model, endpoint=endpoint)
            self.audit.log("key_access", f"check_key:{key_name}", True, detail=f"model={model}")
            return result
        except PermissionDenied as e:
            self.audit.log("key_access", f"check_key:{key_name}", False, detail=str(e), severity="warning")
            raise

    def check_network(self, url: str) -> bool:
        """Check if a URL is accessible."""
        result = self.network.check_access(url, agent_id=self._agent_id)
        self.audit.log("network", url, result, severity="warning" if not result else "info")
        return result

    def check_file(self, path: str, operation: str = "read") -> bool:
        """Check if a file operation is allowed."""
        result = self.fs.check_access(path, operation)
        self.audit.log("filesystem", f"{operation}:{path}", result, severity="warning" if not result else "info")
        return result

    def kill(self) -> None:
        """Activate the kill switch — blocks all network egress immediately."""
        self.network.activate_kill_switch()
        self.audit.log("system", "kill_switch_activated", True, severity="critical")

    def resume(self) -> None:
        """Deactivate the kill switch."""
        self.network.deactivate_kill_switch()
        self.audit.log("system", "kill_switch_deactivated", True)

    @property
    def is_killed(self) -> bool:
        return self.network.is_kill_switch_active

    def audit_summary(self) -> dict:
        """Return a combined audit summary."""
        return {
            "agent_id": self._agent_id,
            "kill_switch": self.is_killed,
            "keys_loaded": self.vault.key_count,
            "allowed_domains": self.network.get_allowed_domains(),
            "allowed_dirs": self.fs.allowed_dirs,
            "audit": self.audit.summary(),
            "network_blocked": self.network.get_blocked_count(),
            "fs_violations": len(self.fs.get_violations()),
        }
