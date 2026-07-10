"""Egress filter: allowlist enforcement for outbound agent traffic.

Default-deny: anything not explicitly allowed is blocked. Supports exact hosts,
wildcard prefixes (``*.api.github.com``), and CIDR ranges for IP literals.
"""
from __future__ import annotations

import ipaddress
from dataclasses import dataclass, field
from typing import List, Tuple


@dataclass(frozen=True)
class EgressRule:
    """A single allowlist rule. ``pattern`` may be an exact host, a wildcard
    prefix (``*.example.com``), or a CIDR (``10.0.0.0/8``)."""

    pattern: str
    ports: Tuple[int, ...] = ()  # empty = any port

    def matches(self, host: str, port: int | None = None) -> bool:
        host = host.strip().lower()
        pat = self.pattern.strip().lower()

        # CIDR match (only for IP literals)
        if "/" in pat:
            try:
                net = ipaddress.ip_network(pat, strict=False)
                addr = ipaddress.ip_address(host)
                if addr not in net:
                    return False
                return self._port_ok(port)
            except (ValueError, ipaddress.AddressValueError):
                return False

        # Wildcard prefix: *.example.com matches sub.example.com and example.com
        if pat.startswith("*."):
            base = pat[2:]
            if host == base or host.endswith("." + base):
                return self._port_ok(port)
            return False

        # Exact host
        if host == pat:
            return self._port_ok(port)
        return False

    def _port_ok(self, port: int | None) -> bool:
        if not self.ports:
            return True
        if port is None:
            return True
        return port in self.ports


class EgressFilter:
    """Allowlist-based egress decision maker. Default-deny when no rules present."""

    def __init__(self, rules: List[EgressRule] | None = None) -> None:
        self._rules: List[EgressRule] = list(rules or [])

    def add_rule(self, pattern: str, ports: Tuple[int, ...] = ()) -> EgressRule:
        rule = EgressRule(pattern=pattern, ports=ports)
        self._rules.append(rule)
        return rule

    def allow(self, host: str, port: int | None = None) -> bool:
        """Default-deny: allowed only if at least one rule matches."""
        if not self._rules:
            return False
        return any(r.matches(host, port) for r in self._rules)

    def check(self, host: str, port: int | None = None) -> None:
        """Raise EgressDeniedError on deny; return None on allow."""
        if not self.allow(host, port):
            from agentvault.vault import EgressDeniedError

            raise EgressDeniedError(host, port)

    @property
    def rules(self) -> List[EgressRule]:
        return list(self._rules)

    def to_jsonable(self) -> List[dict]:
        return [{"pattern": r.pattern, "ports": list(r.ports)} for r in self._rules]
