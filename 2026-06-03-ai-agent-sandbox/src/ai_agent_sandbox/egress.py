"""Network Egress Control — Allowlist-based network access for AI agents.

Monitors and controls which domains/endpoints an AI agent can reach.
Designed to be used as a local proxy or imported as a library for agent wrappers.
"""

from __future__ import annotations

import time
import threading
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urlparse


@dataclass
class EgressRule:
    """A single allowlist rule for network egress."""
    domain: str  # e.g. "api.openai.com"
    ports: tuple[int, ...] = (443, 80)
    description: str = ""

    def matches(self, url: str) -> bool:
        """Check if a URL matches this rule."""
        parsed = urlparse(url)
        hostname = parsed.hostname or ""
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        return hostname == self.domain and port in self.ports


@dataclass
class EgressEvent:
    """Record of a network access attempt."""
    timestamp: float
    url: str
    allowed: bool
    agent_id: str = "default"
    reason: str = ""


class NetworkEgressController:
    """Controls network access for AI agents using an allowlist model.

    Default policy: deny all, allow only explicitly permitted domains.

    Usage:
        controller = NetworkEgressController(default_deny=True)
        controller.allow_domain("api.openai.com", description="OpenAI API")
        controller.allow_domain("api.anthropic.com", description="Anthropic API")

        if controller.check_access("https://api.openai.com/v1/chat"):
            # proceed with request
        else:
            # block and log
    """

    def __init__(self, default_deny: bool = True) -> None:
        self._rules: list[EgressRule] = []
        self._default_deny = default_deny
        self._events: list[EgressEvent] = []
        self._lock = threading.Lock()
        self._kill_switch = False

    def allow_domain(
        self,
        domain: str,
        ports: tuple[int, ...] = (443, 80),
        description: str = "",
    ) -> None:
        """Add a domain to the allowlist."""
        with self._lock:
            # Remove existing rule for this domain to avoid duplicates
            self._rules = [r for r in self._rules if r.domain != domain]
            self._rules.append(EgressRule(domain=domain, ports=ports, description=description))

    def deny_domain(self, domain: str) -> None:
        """Explicitly deny a domain (removes from allowlist)."""
        with self._lock:
            self._rules = [r for r in self._rules if r.domain != domain]

    def check_access(self, url: str, agent_id: str = "default") -> bool:
        """Check if a URL is accessible under the current policy.

        Returns:
            True if the URL is allowed.
        """
        if self._kill_switch:
            event = EgressEvent(
                timestamp=time.time(),
                url=url,
                allowed=False,
                agent_id=agent_id,
                reason="kill_switch_active",
            )
            with self._lock:
                self._events.append(event)
            return False

        allowed = False
        for rule in self._rules:
            if rule.matches(url):
                allowed = True
                break

        if not allowed and not self._default_deny:
            allowed = True

        event = EgressEvent(
            timestamp=time.time(),
            url=url,
            allowed=allowed,
            agent_id=agent_id,
            reason="matched_rule" if allowed else "no_matching_rule",
        )
        with self._lock:
            self._events.append(event)

        return allowed

    def activate_kill_switch(self) -> None:
        """Immediately block all network egress."""
        with self._lock:
            self._kill_switch = True

    def deactivate_kill_switch(self) -> None:
        """Re-enable network access."""
        with self._lock:
            self._kill_switch = False

    @property
    def is_kill_switch_active(self) -> bool:
        return self._kill_switch

    def get_events(self, agent_id: str = "", since: float = 0) -> list[EgressEvent]:
        """Get network access events, optionally filtered."""
        with self._lock:
            events = list(self._events)
        if agent_id:
            events = [e for e in events if e.agent_id == agent_id]
        if since:
            events = [e for e in events if e.timestamp >= since]
        return events

    def get_blocked_count(self) -> int:
        """Return the number of blocked requests."""
        with self._lock:
            return sum(1 for e in self._events if not e.allowed)

    def get_allowed_domains(self) -> list[str]:
        """Return the list of allowed domains."""
        with self._lock:
            return [r.domain for r in self._rules]
