"""ModelRouter — GLM-5.2 OpenAI-compatible gateway with fallback, health checks, and cost tracking."""

from __future__ import annotations

import time
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class Provider:
    """An OpenAI-compatible LLM provider."""
    name: str
    base_url: str
    api_key: str = ""
    model_map: dict[str, str] = field(default_factory=dict)
    input_cost_per_mtok: float = 0.0   # cost per million input tokens
    output_cost_per_mtok: float = 0.0  # cost per million output tokens
    timeout_seconds: float = 30.0

    def resolve_model(self, model: str) -> str:
        """Map an OpenAI model name to this provider's model name."""
        return self.model_map.get(model, model)

    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost in USD for a request."""
        return (input_tokens * self.input_cost_per_mtok + output_tokens * self.output_cost_per_mtok) / 1_000_000


@dataclass
class RouteResult:
    """Result of a routed request."""
    model: str
    provider: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    fallback_used: bool = False
    latency_ms: float = 0.0
    success: bool = True
    error: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    response: dict[str, Any] = field(default_factory=dict)


@dataclass
class HealthStatus:
    """Health check result for a provider."""
    provider: str
    healthy: bool
    latency_ms: float = 0.0
    checked_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    error: str = ""


class CircuitBreaker:
    """Circuit breaker for provider health."""

    def __init__(self, failure_threshold: int = 3, recovery_seconds: float = 60.0):
        self._failure_threshold = failure_threshold
        self._recovery_seconds = recovery_seconds
        self._failures: dict[str, int] = {}
        self._last_failure: dict[str, float] = {}
        self._lock = threading.Lock()

    @property
    def failure_threshold(self) -> int:
        return self._failure_threshold

    @property
    def recovery_seconds(self) -> float:
        return self._recovery_seconds

    def is_open(self, provider_name: str) -> bool:
        """Check if circuit is open (provider is blocked)."""
        with self._lock:
            failures = self._failures.get(provider_name, 0)
            if failures < self._failure_threshold:
                return False
            last_fail = self._last_failure.get(provider_name, 0.0)
            if time.monotonic() - last_fail >= self._recovery_seconds:
                # Recovery period elapsed, allow one request through
                return False
            return True

    def record_success(self, provider_name: str) -> None:
        with self._lock:
            self._failures.pop(provider_name, None)
            self._last_failure.pop(provider_name, None)

    def record_failure(self, provider_name: str) -> None:
        with self._lock:
            self._failures[provider_name] = self._failures.get(provider_name, 0) + 1
            self._last_failure[provider_name] = time.monotonic()

    def reset(self, provider_name: str) -> None:
        with self._lock:
            self._failures.pop(provider_name, None)
            self._last_failure.pop(provider_name, None)


class Router:
    """Routes OpenAI-format requests to providers with fallback and cost tracking."""

    def __init__(
        self,
        primary: Provider,
        fallback: Provider | None = None,
        circuit_breaker: CircuitBreaker | None = None,
    ):
        self.primary = primary
        self.fallback = fallback
        self.circuit = circuit_breaker or CircuitBreaker()
        self._request_log: list[RouteResult] = []
        self._lock = threading.Lock()

    def route(
        self,
        model: str,
        messages: list[dict[str, str]],
        input_tokens: int = 0,
        output_tokens: int = 0,
        **kwargs: Any,
    ) -> RouteResult:
        """Route a request to the primary provider, falling back on failure."""
        start = time.monotonic()

        # Try primary
        if not self.circuit.is_open(self.primary.name):
            resolved = self.primary.resolve_model(model)
            cost = self.primary.calculate_cost(input_tokens, output_tokens)
            latency = (time.monotonic() - start) * 1000
            result = RouteResult(
                model=resolved,
                provider=self.primary.name,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost,
                fallback_used=False,
                latency_ms=latency,
                success=True,
            )
            self.circuit.record_success(self.primary.name)
            self._log(result)
            return result

        # Try fallback
        if self.fallback and not self.circuit.is_open(self.fallback.name):
            resolved = self.fallback.resolve_model(model)
            cost = self.fallback.calculate_cost(input_tokens, output_tokens)
            latency = (time.monotonic() - start) * 1000
            result = RouteResult(
                model=resolved,
                provider=self.fallback.name,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost,
                fallback_used=True,
                latency_ms=latency,
                success=True,
            )
            self.circuit.record_success(self.fallback.name)
            self._log(result)
            return result

        # All providers unavailable
        latency = (time.monotonic() - start) * 1000
        result = RouteResult(
            model=model,
            provider="none",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=0.0,
            fallback_used=False,
            latency_ms=latency,
            success=False,
            error="All providers unavailable (circuit open)",
        )
        self._log(result)
        return result

    def mark_unhealthy(self, provider_name: str) -> None:
        """Mark a provider as unhealthy (opens circuit)."""
        self.circuit.record_failure(provider_name)

    def health_check(self, provider: Provider | None = None) -> HealthStatus:
        """Check health of a provider (or primary if not specified)."""
        target = provider or self.primary
        start = time.monotonic()
        # Simulate health check — in production this would make a lightweight API call
        latency = (time.monotonic() - start) * 1000
        is_open = self.circuit.is_open(target.name)
        return HealthStatus(
            provider=target.name,
            healthy=not is_open,
            latency_ms=latency,
            error="" if not is_open else "Circuit breaker open",
        )

    @property
    def request_log(self) -> list[RouteResult]:
        """Return a copy of the request log."""
        with self._lock:
            return list(self._request_log)

    def total_cost(self) -> float:
        """Total cost of all logged requests."""
        with self._lock:
            return sum(r.cost_usd for r in self._request_log)

    def total_requests(self) -> int:
        """Total number of logged requests."""
        with self._lock:
            return len(self._request_log)

    def fallback_count(self) -> int:
        """Number of requests that used fallback."""
        with self._lock:
            return sum(1 for r in self._request_log if r.fallback_used)

    def _log(self, result: RouteResult) -> None:
        with self._lock:
            self._request_log.append(result)
