"""Tests for MCP Tool Scout."""

from __future__ import annotations

import pytest
from mcp_tool_scout import McpServer, ScoreBreakdown, ScoringEngine, ServerStore


# ── Fixtures ────────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_server() -> McpServer:
    return McpServer(
        name="test-mcp",
        slug="test-mcp",
        description="A test MCP server for unit tests",
        repo_url="https://github.com/example/test-mcp",
        stars=500,
        forks=50,
        watchers=20,
        open_issues=10,
        language="Python",
        topics=["mcp", "test", "python"],
        readme_snippet="This is a test MCP server with a decent README that has enough words to score well on documentation metrics",
        last_push="2026-05-28T10:00:00Z",
        created_at="2025-06-01T00:00:00Z",
    )


@pytest.fixture
def popular_server() -> McpServer:
    return McpServer(
        name="popular-mcp",
        slug="popular-mcp",
        description="A very popular MCP server",
        repo_url="https://github.com/example/popular-mcp",
        stars=10000,
        forks=800,
        watchers=300,
        open_issues=25,
        language="TypeScript",
        topics=["mcp", "typescript", "ai", "agents", "tools"],
        readme_snippet="This is an extremely popular MCP server with comprehensive documentation and many features for AI agents to use in their workflows",
        last_push="2026-05-30T08:00:00Z",
        created_at="2025-01-01T00:00:00Z",
    )


@pytest.fixture
def stale_server() -> McpServer:
    return McpServer(
        name="stale-mcp",
        slug="stale-mcp",
        description="An old unmaintained MCP server",
        repo_url="https://github.com/example/stale-mcp",
        stars=15,
        forks=2,
        watchers=3,
        open_issues=40,
        language="Python",
        topics=["mcp"],
        readme_snippet="Old server",
        last_push="2025-01-01T00:00:00Z",
        created_at="2024-06-01T00:00:00Z",
    )


@pytest.fixture
def empty_store() -> ServerStore:
    return ServerStore()


@pytest.fixture
def populated_store(sample_server, popular_server, stale_server) -> ServerStore:
    store = ServerStore()
    for s in [sample_server, popular_server, stale_server]:
        store.upsert(s)
    return store


# ── ScoringEngine Tests ─────────────────────────────────────────────────────────

class TestScoringEngine:
    def test_score_returns_float(self, sample_server):
        engine = ScoringEngine()
        score = engine.score(sample_server)
        assert isinstance(score, float)
        assert 0 <= score <= 100

    def test_popular_server_scores_higher(self, sample_server, popular_server):
        engine = ScoringEngine()
        assert engine.score(popular_server) > engine.score(sample_server)

    def test_stale_server_scores_low(self, sample_server, stale_server):
        engine = ScoringEngine()
        assert engine.score(sample_server) > engine.score(stale_server)

    def test_breakdown_returns_all_fields(self, sample_server):
        engine = ScoringEngine()
        bd = engine.breakdown(sample_server)
        assert isinstance(bd, ScoreBreakdown)
        assert bd.server_name == "test-mcp"
        assert 0 <= bd.popularity_score <= 100
        assert 0 <= bd.activity_score <= 100
        assert 0 <= bd.documentation_score <= 100
        assert 0 <= bd.freshness_score <= 100
        assert 0 <= bd.total_score <= 100
        assert len(bd.recommendation) > 0

    def test_popular_gets_highly_recommended(self, popular_server):
        engine = ScoringEngine()
        bd = engine.breakdown(popular_server)
        assert "recommended" in bd.recommendation.lower() or "Highly" in bd.recommendation

    def test_stale_gets_warning(self, stale_server):
        engine = ScoringEngine()
        bd = engine.breakdown(stale_server)
        # Stale server should not get a strong recommendation
        assert bd.total_score < 60

    def test_score_is_deterministic(self, sample_server):
        engine = ScoringEngine()
        assert engine.score(sample_server) == engine.score(sample_server)

    def test_weights_sum_to_one(self):
        engine = ScoringEngine()
        total = engine.POPULARITY_WEIGHT + engine.ACTIVITY_WEIGHT + engine.DOCS_WEIGHT + engine.FRESHNESS_WEIGHT
        assert abs(total - 1.0) < 0.001


# ── ServerStore Tests ───────────────────────────────────────────────────────────

class TestServerStore:
    def test_upsert_and_get(self, empty_store, sample_server):
        empty_store.upsert(sample_server)
        retrieved = empty_store.get(sample_server.id)
        assert retrieved is not None
        assert retrieved.name == "test-mcp"

    def test_upsert_sets_score(self, empty_store, sample_server):
        empty_store.upsert(sample_server)
        retrieved = empty_store.get(sample_server.id)
        assert retrieved.score > 0
        assert retrieved.scored_at is not None

    def test_get_missing_returns_none(self, empty_store):
        assert empty_store.get("nonexistent") is None

    def test_search_all(self, populated_store):
        result = populated_store.search()
        assert result.total == 3
        assert len(result.results) == 3

    def test_search_by_name(self, populated_store):
        result = populated_store.search(query="popular")
        assert result.total == 1
        assert result.results[0].name == "popular-mcp"

    def test_search_by_topic(self, populated_store):
        result = populated_store.search(query="typescript")
        assert result.total >= 1

    def test_search_min_score(self, populated_store):
        result = populated_store.search(min_score=50)
        for s in result.results:
            assert s.score >= 50

    def test_search_sorted_by_score(self, populated_store):
        result = populated_store.search(sort="score")
        scores = [s.score for s in result.results]
        assert scores == sorted(scores, reverse=True)

    def test_search_sorted_by_stars(self, populated_store):
        result = populated_store.search(sort="stars")
        stars = [s.stars for s in result.results]
        assert stars == sorted(stars, reverse=True)

    def test_search_pagination(self, populated_store):
        result = populated_store.search(page=1, per_page=2)
        assert len(result.results) == 2
        assert result.total == 3

    def test_all_returns_sorted(self, populated_store):
        all_servers = populated_store.all()
        assert len(all_servers) == 3
        scores = [s.score for s in all_servers]
        assert scores == sorted(scores, reverse=True)

    def test_count(self, populated_store):
        assert populated_store.count == 3

    def test_upsert_updates(self, empty_store, sample_server):
        empty_store.upsert(sample_server)
        sample_server.stars = 9999
        empty_store.upsert(sample_server)
        assert empty_store.count == 1
        assert empty_store.get(sample_server.id).stars == 9999


# ── McpServer Model Tests ──────────────────────────────────────────────────────

class TestMcpServer:
    def test_id_is_deterministic(self, sample_server):
        assert sample_server.id == sample_server.id

    def test_id_is_unique_per_url(self):
        a = McpServer(name="a", slug="a", repo_url="https://github.com/a")
        b = McpServer(name="b", slug="b", repo_url="https://github.com/b")
        assert a.id != b.id

    def test_defaults(self):
        s = McpServer(name="x", slug="x", repo_url="https://example.com")
        assert s.stars == 0
        assert s.forks == 0
        assert s.score == 0.0
        assert s.topics == []
        assert s.description == ""


# ── Seed Data Tests ─────────────────────────────────────────────────────────────

class TestSeedData:
    def test_seed_populates_store(self, empty_store):
        from mcp_tool_scout import seed_store
        seed_store(empty_store)
        assert empty_store.count > 0

    def test_seed_servers_have_scores(self, empty_store):
        from mcp_tool_scout import seed_store
        seed_store(empty_store)
        for s in empty_store.all():
            assert s.score > 0
            assert s.scored_at is not None

    def test_seed_searchable(self, empty_store):
        from mcp_tool_scout import seed_store
        seed_store(empty_store)
        result = empty_store.search(query="github")
        assert result.total >= 1
