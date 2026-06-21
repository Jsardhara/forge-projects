"""Tests for Router, RouteResult, HealthStatus, and CircuitBreaker."""

import time
import pytest
from model_router import Provider, Router, RouteResult, HealthStatus, CircuitBreaker


@pytest.fixture
def glm():
    return Provider(
        name="glm-5.2",
        base_url="https://api.z.ai/v1",
        api_key="test-key",
        model_map={"gpt-4o": "z-ai/glm-5.2"},
        input_cost_per_mtok=1.40,
        output_cost_per_mtok=4.40,
    )


@pytest.fixture
def openai():
    return Provider(
        name="openai",
        base_url="https://api.openai.com/v1",
        api_key="sk-test",
        model_map={},
        input_cost_per_mtok=5.0,
        output_cost_per_mtok=15.0,
    )


@pytest.fixture
def router(glm, openai):
    return Router(primary=glm, fallback=openai)


class TestRouteResult:
    def test_default_timestamp(self):
        r = RouteResult(model="test", provider="p1")
        assert r.timestamp  # non-empty string

    def test_default_success(self):
        r = RouteResult(model="test", provider="p1")
        assert r.success is True

    def test_default_fallback_used(self):
        r = RouteResult(model="test", provider="p1")
        assert r.fallback_used is False


class TestHealthStatus:
    def test_default_healthy(self):
        h = HealthStatus(provider="test", healthy=True)
        assert h.error == ""

    def test_checked_at_set(self):
        h = HealthStatus(provider="test", healthy=True)
        assert h.checked_at  # non-empty


class TestCircuitBreaker:
    def test_initially_closed(self):
        cb = CircuitBreaker()
        assert cb.is_open("any-provider") is False

    def test_opens_after_threshold(self):
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure("p1")
        cb.record_failure("p1")
        assert cb.is_open("p1") is False  # not yet at threshold
        cb.record_failure("p1")
        assert cb.is_open("p1") is True  # now open

    def test_success_resets(self):
        cb = CircuitBreaker(failure_threshold=2)
        cb.record_failure("p1")
        cb.record_failure("p1")
        assert cb.is_open("p1") is True
        cb.record_success("p1")
        assert cb.is_open("p1") is False

    def test_reset(self):
        cb = CircuitBreaker(failure_threshold=1)
        cb.record_failure("p1")
        assert cb.is_open("p1") is True
        cb.reset("p1")
        assert cb.is_open("p1") is False

    def test_per_provider_isolation(self):
        cb = CircuitBreaker(failure_threshold=2)
        cb.record_failure("p1")
        cb.record_failure("p1")
        assert cb.is_open("p1") is True
        assert cb.is_open("p2") is False  # p2 unaffected

    def test_recovery_after_timeout(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_seconds=0.1)
        cb.record_failure("p1")
        assert cb.is_open("p1") is True
        time.sleep(0.15)
        assert cb.is_open("p1") is False  # recovery period elapsed

    def test_properties(self):
        cb = CircuitBreaker(failure_threshold=5, recovery_seconds=120)
        assert cb.failure_threshold == 5
        assert cb.recovery_seconds == 120


class TestRouterRoute:
    def test_routes_to_primary(self, router, glm):
        result = router.route(model="gpt-4o", messages=[{"role": "user", "content": "hi"}])
        assert result.provider == "glm-5.2"
        assert result.success is True

    def test_resolves_model_name(self, router):
        result = router.route(model="gpt-4o", messages=[{"role": "user", "content": "hi"}])
        assert result.model == "z-ai/glm-5.2"

    def test_calculates_cost(self, router):
        result = router.route(model="gpt-4o", messages=[], input_tokens=1000, output_tokens=500)
        expected = (1000 * 1.40 + 500 * 4.40) / 1_000_000
        assert result.cost_usd == pytest.approx(expected, rel=1e-6)

    def test_fallback_on_circuit_open(self, router, openai):
        for _ in range(3):
            router.mark_unhealthy("glm-5.2")
        result = router.route(model="gpt-4o", messages=[])
        assert result.provider == "openai"
        assert result.fallback_used is True

    def test_fallback_cost_uses_fallback_rates(self, router, openai):
        for _ in range(3):
            router.mark_unhealthy("glm-5.2")
        result = router.route(model="gpt-4o", messages=[], input_tokens=1000, output_tokens=500)
        expected = (1000 * 5.0 + 500 * 15.0) / 1_000_000
        assert result.cost_usd == pytest.approx(expected, rel=1e-6)

    def test_all_unhealthy_returns_error(self, router):
        for _ in range(3):
            router.mark_unhealthy("glm-5.2")
        for _ in range(3):
            router.mark_unhealthy("openai")
        result = router.route(model="gpt-4o", messages=[])
        assert result.success is False
        assert result.provider == "none"
        assert "unavailable" in result.error.lower()

    def test_no_fallback_returns_error(self, glm):
        router = Router(primary=glm)
        for _ in range(3):
            router.mark_unhealthy("glm-5.2")
        result = router.route(model="gpt-4o", messages=[])
        assert result.success is False

    def test_latency_recorded(self, router):
        result = router.route(model="gpt-4o", messages=[])
        assert result.latency_ms >= 0.0

    def test_timestamp_set(self, router):
        result = router.route(model="gpt-4o", messages=[])
        assert result.timestamp  # non-empty


class TestRouterLog:
    def test_request_logged(self, router):
        router.route(model="gpt-4o", messages=[])
        assert router.total_requests() == 1

    def test_multiple_requests_logged(self, router):
        for _ in range(5):
            router.route(model="gpt-4o", messages=[])
        assert router.total_requests() == 5

    def test_total_cost_accumulates(self, router):
        for _ in range(3):
            router.route(model="gpt-4o", messages=[], input_tokens=1000, output_tokens=500)
        expected_single = (1000 * 1.40 + 500 * 4.40) / 1_000_000
        assert router.total_cost() == pytest.approx(expected_single * 3, rel=1e-6)

    def test_fallback_count(self, router):
        router.route(model="gpt-4o", messages=[])
        for _ in range(3):
            router.mark_unhealthy("glm-5.2")
        router.route(model="gpt-4o", messages=[])
        assert router.fallback_count() == 1

    def test_request_log_returns_copy(self, router):
        router.route(model="gpt-4o", messages=[])
        log = router.request_log
        log.clear()
        assert router.total_requests() == 1  # original not mutated


class TestRouterHealthCheck:
    def test_primary_healthy(self, router):
        status = router.health_check()
        assert status.healthy is True
        assert status.provider == "glm-5.2"

    def test_unhealthy_after_failures(self, router):
        for _ in range(3):
            router.mark_unhealthy("glm-5.2")
        status = router.health_check()
        assert status.healthy is False
        assert "circuit" in status.error.lower()

    def test_custom_provider_health(self, router, openai):
        status = router.health_check(openai)
        assert status.provider == "openai"
        assert status.healthy is True
