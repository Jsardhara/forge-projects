"""Tests for Provider model."""

import pytest
from model_router import Provider


@pytest.fixture
def glm_provider():
    return Provider(
        name="glm-5.2",
        base_url="https://api.z.ai/v1",
        api_key="test-key",
        model_map={"gpt-4o": "z-ai/glm-5.2", "gpt-4o-mini": "z-ai/glm-5.2"},
        input_cost_per_mtok=1.40,
        output_cost_per_mtok=4.40,
    )


@pytest.fixture
def openai_provider():
    return Provider(
        name="openai",
        base_url="https://api.openai.com/v1",
        api_key="sk-test",
        model_map={},
        input_cost_per_mtok=5.0,
        output_cost_per_mtok=15.0,
    )


class TestProviderResolveModel:
    def test_maps_gpt4o_to_glm(self, glm_provider):
        assert glm_provider.resolve_model("gpt-4o") == "z-ai/glm-5.2"

    def test_maps_gpt4o_mini_to_glm(self, glm_provider):
        assert glm_provider.resolve_model("gpt-4o-mini") == "z-ai/glm-5.2"

    def test_unknown_model_passthrough(self, glm_provider):
        assert glm_provider.resolve_model("claude-3") == "claude-3"

    def test_empty_model_map_passthrough(self, openai_provider):
        assert openai_provider.resolve_model("gpt-4o") == "gpt-4o"

    def test_empty_model_string(self, glm_provider):
        assert glm_provider.resolve_model("") == ""


class TestProviderCalculateCost:
    def test_glm_cost_basic(self, glm_provider):
        cost = glm_provider.calculate_cost(1000, 500)
        expected = (1000 * 1.40 + 500 * 4.40) / 1_000_000
        assert cost == pytest.approx(expected, rel=1e-6)

    def test_glm_cost_zero_tokens(self, glm_provider):
        assert glm_provider.calculate_cost(0, 0) == 0.0

    def test_glm_cost_large(self, glm_provider):
        cost = glm_provider.calculate_cost(1_000_000, 500_000)
        expected = (1_000_000 * 1.40 + 500_000 * 4.40) / 1_000_000
        assert cost == pytest.approx(expected, rel=1e-6)

    def test_openai_cost_higher_than_glm(self, glm_provider, openai_provider):
        tokens = (10000, 5000)
        assert openai_provider.calculate_cost(*tokens) > glm_provider.calculate_cost(*tokens)

    def test_cost_with_zero_output(self, glm_provider):
        cost = glm_provider.calculate_cost(1000, 0)
        expected = (1000 * 1.40) / 1_000_000
        assert cost == pytest.approx(expected, rel=1e-6)

    def test_cost_with_zero_input(self, glm_provider):
        cost = glm_provider.calculate_cost(0, 1000)
        expected = (1000 * 4.40) / 1_000_000
        assert cost == pytest.approx(expected, rel=1e-6)


class TestProviderDefaults:
    def test_default_costs_are_zero(self):
        p = Provider(name="test", base_url="http://localhost")
        assert p.input_cost_per_mtok == 0.0
        assert p.output_cost_per_mtok == 0.0
        assert p.calculate_cost(1000, 500) == 0.0

    def test_default_timeout(self, glm_provider):
        assert glm_provider.timeout_seconds == 30.0

    def test_default_model_map_empty(self):
        p = Provider(name="test", base_url="http://localhost")
        assert p.model_map == {}
