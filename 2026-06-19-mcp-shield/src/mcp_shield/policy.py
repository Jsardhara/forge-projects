"""Policy engine for MCP tool-call authorization with allow/deny rules."""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class PolicyAction(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"


@dataclass
class PolicyDecision:
    action: PolicyAction
    reason: str
    rule_name: str = ""
    risk_score: float = 0.0


@dataclass
class PolicyRule:
    """A single allow/deny rule for MCP tool access."""
    name: str
    action: PolicyAction
    agent_pattern: str = "*"
    tool_pattern: str = "*"
    server_pattern: str = "*"
    max_calls_per_minute: int = 0  # 0 = unlimited
    risk_threshold: float = 1.0  # 1.0 = any risk denies
    time_window: Optional[str] = None  # "09:00-17:00" or None for always
    priority: int = 0  # higher = evaluated first
    scope: str = ""
    enabled: bool = True


class PolicyEngine:
    """
    Rule-based policy engine for MCP tool-call authorization.

    Evaluates tool-call requests against a set of allow/deny rules.
    Deny rules take precedence. Rate limiting is per-agent+tool.

    Rule evaluation order:
    1. Deny rules (matched first = immediate deny)
    2. Allow rules (matched = allow with constraints)
    3. Default deny (if no allow rule matches)
    """

    def __init__(self, rules: Optional[list[PolicyRule]] = None):
        self._rules: list[PolicyRule] = sorted(
            rules or [], key=lambda r: r.priority, reverse=True
        )
        self._call_counters: dict[str, list[str]] = {}  # key -> list of timestamps

    @property
    def rules(self) -> list[PolicyRule]:
        return list(self._rules)

    def add_rule(self, rule: PolicyRule) -> None:
        self._rules.append(rule)
        self._rules.sort(key=lambda r: r.priority, reverse=True)

    def remove_rule(self, name: str) -> bool:
        before = len(self._rules)
        self._rules = [r for r in self._rules if r.name != name]
        return len(self._rules) < before

    def evaluate(
        self,
        *,
        agent_id: str,
        tool_name: str,
        server_id: str,
        arguments: Optional[dict] = None,
    ) -> PolicyDecision:
        """Evaluate a tool-call request against the policy rules."""
        now = datetime.now(timezone.utc)

        # Check deny rules first
        for rule in self._rules:
            if not rule.enabled:
                continue
            if rule.action != PolicyAction.DENY:
                continue
            if self._matches(rule, agent_id, tool_name, server_id, now):
                risk = self._calculate_risk(agent_id, tool_name, arguments)
                return PolicyDecision(
                    action=PolicyAction.DENY,
                    reason=f"Denied by rule '{rule.name}'",
                    rule_name=rule.name,
                    risk_score=risk,
                )

        # Check allow rules
        for rule in self._rules:
            if not rule.enabled:
                continue
            if rule.action == PolicyAction.DENY:
                continue
            if self._matches(rule, agent_id, tool_name, server_id, now):
                # Check rate limit if applicable
                if rule.max_calls_per_minute > 0:
                    if not self._check_rate_limit(
                        agent_id, tool_name, rule.max_calls_per_minute, now
                    ):
                        return PolicyDecision(
                            action=PolicyAction.DENY,
                            reason=f"Rate limit exceeded for rule '{rule.name}'",
                            rule_name=rule.name,
                            risk_score=0.5,
                        )

                action = rule.action
                if action == PolicyAction.ALLOW:
                    self._record_call(agent_id, tool_name, now)

                risk = self._calculate_risk(agent_id, tool_name, arguments)
                return PolicyDecision(
                    action=action,
                    reason=f"Matched rule '{rule.name}'",
                    rule_name=rule.name,
                    risk_score=risk,
                )

        # Default: require approval (safe default)
        return PolicyDecision(
            action=PolicyAction.REQUIRE_APPROVAL,
            reason="No matching rule — requires manual approval",
            rule_name="default",
            risk_score=0.3,
        )

    def get_rate_limit_usage(
        self, agent_id: str, tool_name: str
    ) -> tuple[int, int]:
        """Return (used, limit) for the last 60s window. Limit=0 means unlimited."""
        key = f"{agent_id}:{tool_name}"
        now = datetime.now(timezone.utc)
        window_start = now.timestamp() - 60
        timestamps = self._call_counters.get(key, [])
        recent = [t for t in timestamps if t > window_start]
        return len(recent), 0  # limit is rule-specific

    def _matches(
        self,
        rule: PolicyRule,
        agent_id: str,
        tool_name: str,
        server_id: str,
        now: datetime,
    ) -> bool:
        if not fnmatch.fnmatch(agent_id, rule.agent_pattern):
            return False
        if not fnmatch.fnmatch(tool_name, rule.tool_pattern):
            return False
        if not fnmatch.fnmatch(server_id, rule.server_pattern):
            return False
        if rule.time_window and not self._in_time_window(rule.time_window, now):
            return False
        return True

    def _in_time_window(self, window: str, now: datetime) -> bool:
        try:
            start_str, end_str = window.split("-")
            start_h, start_m = map(int, start_str.split(":"))
            end_h, end_m = map(int, end_str.split(":"))
            current_minutes = now.hour * 60 + now.minute
            start_minutes = start_h * 60 + start_m
            end_minutes = end_h * 60 + end_m
            return start_minutes <= current_minutes <= end_minutes
        except (ValueError, AttributeError):
            return True  # malformed window = don't restrict

    def _check_rate_limit(
        self, agent_id: str, tool_name: str, limit: int, now: datetime
    ) -> bool:
        key = f"{agent_id}:{tool_name}"
        window_start = now.timestamp() - 60
        timestamps = self._call_counters.get(key, [])
        recent = [t for t in timestamps if t > window_start]
        return len(recent) < limit

    def _record_call(
        self, agent_id: str, tool_name: str, now: datetime
    ) -> None:
        key = f"{agent_id}:{tool_name}"
        self._call_counters.setdefault(key, []).append(now.timestamp())

    def _calculate_risk(
        self, agent_id: str, tool_name: str, arguments: Optional[dict]
    ) -> float:
        """Heuristic risk score 0.0-1.0 based on tool type and arguments."""
        high_risk_tools = {"exec", "shell", "delete_file", "write_file", "eval"}
        medium_risk_tools = {"fetch", "request", "database_query"}

        base = 0.1
        if tool_name in high_risk_tools:
            base = 0.7
        elif tool_name in medium_risk_tools:
            base = 0.4

        # Elevate risk if arguments contain dangerous patterns
        if arguments:
            args_str = str(arguments)
            dangerous = ["sudo", "rm -rf", "DROP TABLE", "eval(", "exec("]
            for pattern in dangerous:
                if pattern.lower() in args_str.lower():
                    base = min(1.0, base + 0.3)
                    break

        return round(base, 2)
