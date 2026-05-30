"""MCP Tool Scout — discover, score, and search MCP servers for AI agents."""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import AsyncIterator, Optional

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


# ── Domain Models ───────────────────────────────────────────────────────────────

class McpServer(BaseModel):
    """A discovered MCP server entry."""
    name: str
    slug: str
    description: str = ""
    repo_url: str
    stars: int = 0
    forks: int = 0
    watchers: int = 0
    open_issues: int = 0
    language: str = ""
    topics: list[str] = Field(default_factory=list)
    readme_snippet: str = ""
    last_push: Optional[str] = None
    created_at: Optional[str] = None
    score: float = 0.0
    scored_at: Optional[str] = None
    source: str = "github"

    @property
    def id(self) -> str:
        return hashlib.sha256(self.repo_url.encode()).hexdigest()[:12]


class SearchResult(BaseModel):
    """Paginated search results."""
    total: int
    page: int
    per_page: int
    results: list[McpServer]


class ScoreBreakdown(BaseModel):
    """Detailed scoring breakdown."""
    server_name: str
    popularity_score: float
    activity_score: float
    documentation_score: float
    freshness_score: float
    total_score: float
    recommendation: str


# ── Scoring Engine ──────────────────────────────────────────────────────────────

class ScoringEngine:
    """Score MCP servers on quality signals.

    Criteria (0-100 scale):
    - Popularity (30%): stars, forks, watchers
    - Activity (30%): recency of last push, issue responsiveness
    - Documentation (25%): README length, topics presence
    - Freshness (15%): created recently + actively maintained
    """

    POPULARITY_WEIGHT = 0.30
    ACTIVITY_WEIGHT = 0.30
    DOCS_WEIGHT = 0.25
    FRESHNESS_WEIGHT = 0.15

    def score(self, server: McpServer) -> float:
        raw = self._breakdown(server)
        total = (
            raw.popularity_score * self.POPULARITY_WEIGHT
            + raw.activity_score * self.ACTIVITY_WEIGHT
            + raw.documentation_score * self.DOCS_WEIGHT
            + raw.freshness_score * self.FRESHNESS_WEIGHT
        )
        return round(total, 2)

    def breakdown(self, server: McpServer) -> ScoreBreakdown:
        pop, act, doc, fresh = self._raw_signals(server)

        if act >= 70 and pop >= 50:
            rec = "🔥 Highly recommended — active and popular"
        elif act >= 50 and doc >= 60:
            rec = "✅ Good choice — well documented and active"
        elif fresh >= 70:
            rec = "🆕 Rising star — new but promising"
        elif pop >= 40:
            rec = "⭐ Established — solid community backing"
        else:
            rec = "⚠️ Evaluate carefully — limited signals"

        return ScoreBreakdown(
            server_name=server.name,
            popularity_score=round(pop, 1),
            activity_score=round(act, 1),
            documentation_score=round(doc, 1),
            freshness_score=round(fresh, 1),
            total_score=round(
                pop * self.POPULARITY_WEIGHT
                + act * self.ACTIVITY_WEIGHT
                + doc * self.DOCS_WEIGHT
                + fresh * self.FRESHNESS_WEIGHT,
                2,
            ),
            recommendation=rec,
        )

    def _breakdown(self, server: McpServer) -> ScoreBreakdown:
        pop, act, doc, fresh = self._raw_signals(server)
        return ScoreBreakdown(
            server_name=server.name,
            popularity_score=round(pop, 1),
            activity_score=round(act, 1),
            documentation_score=round(doc, 1),
            freshness_score=round(fresh, 1),
            total_score=0.0,
            recommendation="",
        )

    def _raw_signals(
        self, server: McpServer
    ) -> tuple[float, float, float, float]:
        # Popularity: log scale for stars (saturation around 500)
        import math
        popularity = min(100, 100 * math.log1p(server.stars) / math.log1p(500))

        # Activity: inverse of days since push (simplified)
        activity = 50.0
        if server.last_push:
            try:
                last = datetime.fromisoformat(server.last_push.replace("Z", "+00:00"))
                days = (datetime.now(last.tzinfo) - last).days if last.tzinfo else 30
                activity = max(0, 100 - days * 2)
            except Exception:
                activity = 30.0
        # Boost if few open issues relative to stars
        if server.stars > 10 and server.open_issues < 20:
            activity = min(100, activity + 15)

        # Documentation: README length + topics
        doc_score = 0.0
        words = len(server.readme_snippet.split()) if server.readme_snippet else 0
        doc_score += min(50, words / 5)  # up to 50 for README
        doc_score += min(50, len(server.topics) * 10)  # up to 50 for topics

        # Freshness
        freshness = 50.0
        if server.created_at:
            try:
                created = datetime.fromisoformat(
                    server.created_at.replace("Z", "+00:00")
                )
                age_days = (datetime.now(created.tzinfo) - created).days if created.tzinfo else 365
                # Sweet spot: 1-12 months old
                if 30 <= age_days <= 365:
                    freshness = 80.0
                elif age_days < 30:
                    freshness = 60.0
                else:
                    freshness = max(20, 100 - age_days / 10)
            except Exception:
                freshness = 40.0

        return (
            min(100, max(0, popularity)),
            min(100, max(0, activity)),
            min(100, max(0, doc_score)),
            min(100, max(0, freshness)),
        )


# ── In-Memory Store (swap for Postgres/SQLite in prod) ─────────────────────────

class ServerStore:
    """Simple in-memory store for MCP server entries."""

    def __init__(self) -> None:
        self._data: dict[str, McpServer] = {}

    def upsert(self, server: McpServer) -> None:
        engine = ScoringEngine()
        server.score = engine.score(server)
        server.scored_at = datetime.utcnow().isoformat()
        self._data[server.id] = server

    def get(self, server_id: str) -> Optional[McpServer]:
        return self._data.get(server_id)

    def search(
        self,
        query: str = "",
        min_score: float = 0.0,
        sort: str = "score",
        page: int = 1,
        per_page: int = 20,
        limit: int = 0,
    ) -> SearchResult:
        results = [
            s for s in self._data.values() if s.score >= min_score
        ]
        if query:
            q = query.lower()
            results = [
                s for s in results
                if q in s.name.lower()
                or q in s.description.lower()
                or any(q in t.lower() for t in s.topics)
            ]

        reverse = sort in ("score", "stars", "forks")
        results.sort(key=lambda s: getattr(s, sort, s.score), reverse=reverse)

        total = len(results)
        if limit:
            results = results[:limit]
        else:
            start = (page - 1) * per_page
            results = results[start : start + per_page]

        return SearchResult(
            total=total,
            page=page,
            per_page=per_page if not limit else total,
            results=results,
        )

    def all(self) -> list[McpServer]:
        return sorted(self._data.values(), key=lambda s: s.score, reverse=True)

    @property
    def count(self) -> int:
        return len(self._data)


# ── GitHub Collector ────────────────────────────────────────────────────────────

class GitHubCollector:
    """Collect MCP server data from GitHub search API."""

    GITHUB_API = "https://api.github.com"
    MCP_QUERIES = [
        "model-context-protocol stars:>10",
        "MCP server stars:>5",
        "mcp-server language:python stars:>5",
        "mcp-server language:typescript stars:>5",
    ]

    def __init__(self, token: str = "") -> None:
        self._token = token
        self._client: Optional[object] = None

    async def collect(self) -> AsyncIterator[McpServer]:
        """Search GitHub for MCP servers and yield parsed results."""
        import httpx

        headers = {"Accept": "application/vnd.github.v3+json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"

        seen: set[str] = set()

        async with httpx.AsyncClient(headers=headers, timeout=30) as client:
            for query in self.MCP_QUERIES:
                try:
                    resp = await client.get(
                        f"{self._GITHUB_API}/search/repositories",
                        params={"q": query, "sort": "stars", "per_page": 20},
                    )
                    if resp.status_code != 200:
                        logger.warning(
                            "github_search_failed",
                            query=query,
                            status=resp.status_code,
                        )
                        continue

                    data = resp.json()
                    for item in data.get("items", []):
                        if item["full_name"] in seen:
                            continue
                        seen.add(item["full_name"])

                        # Attempt to fetch README
                        readme = ""
                        try:
                            readme_resp = await client.get(
                                f"{self._GITHUB_API}/repos/{item['full_name']}/readme"
                            )
                            if readme_resp.status_code == 200:
                                import base64

                                readme = base64.b64decode(
                                    readme_resp.json().get("content", "")
                                ).decode("utf-8", errors="replace")[:2000]
                        except Exception:
                            pass

                        yield McpServer(
                            name=item["name"],
                            slug=item["name"].lower().replace(" ", "-"),
                            description=item.get("description", "") or "",
                            repo_url=item["html_url"],
                            stars=item.get("stargazers_count", 0),
                            forks=item.get("forks_count", 0),
                            watchers=item.get("subscribers_count", 0),
                            open_issues=item.get("open_issues_count", 0),
                            language=item.get("language", "") or "",
                            topics=item.get("topics", []),
                            readme_snippet=readme[:500],
                            last_push=item.get("pushed_at"),
                            created_at=item.get("created_at"),
                            source="github",
                        )
                except Exception as exc:
                    logger.error("collection_error", query=query, error=str(exc))


# ── Seed Data (fallback when GitHub API is rate-limited) ────────────────────────────────

def seed_store(store: ServerStore) -> None:
    """Populate with known high-quality MCP servers as fallback data."""
    seeds = [
        McpServer(
            name="mcp-github",
            slug="mcp-github",
            description="Official GitHub MCP server — repos, PRs, issues, CI",
            repo_url="https://github.com/github/github-mcp-server",
            stars=8500,
            forks=620,
            watchers=120,
            open_issues=45,
            language="Go",
            topics=["github", "mcp", "devtools", "ai"],
            readme_snippet="The GitHub MCP server provides comprehensive access to GitHub repositories, pull requests, issues",
            last_push="2026-05-28T10:00:00Z",
            created_at="2025-01-15T00:00:00Z",
        ),
        McpServer(
            name="filesystem-mcp",
            slug="filesystem-mcp",
            description="Read/write local filesystem access for AI agents",
            repo_url="https://github.com/modelcontextprotocol/servers",
            stars=12000,
            forks=950,
            watchers=200,
            open_issues=78,
            language="TypeScript",
            topics=["mcp", "filesystem", "local", "ai-agents"],
            readme_snippet="Reference implementations for the Model Context Protocol servers including filesystem access",
            last_push="2026-05-29T14:30:00Z",
            created_at="2024-11-01T00:00:00Z",
        ),
        McpServer(
            name="mcp-aws",
            slug="mcp-aws",
            description="Query AWS resources and metrics via MCP",
            repo_url="https://github.com/awslabs/mcp-aws",
            stars=3200,
            forks=280,
            watchers=85,
            open_issues=32,
            language="Python",
            topics=["aws", "mcp", "cloud", "infrastructure"],
            readme_snippet="AWS MCP server enabling AI agents to query CloudWatch, EC2, S3 and other AWS services natively",
            last_push="2026-05-20T09:00:00Z",
            created_at="2025-03-01T00:00:00Z",
        ),
        McpServer(
            name="postgres-mcp",
            slug="postgres-mcp",
            description="Natural language queries against PostgreSQL databases",
            repo_url="https://github.com/modelcontextprotocol/postgres-server",
            stars=4100,
            forks=350,
            watchers=95,
            open_issues=28,
            language="TypeScript",
            topics=["postgres", "database", "mcp", "sql"],
            readme_snippet="PostgreSQL MCP server for querying databases with natural language",
            last_push="2026-05-27T16:00:00Z",
            created_at="2025-02-15T00:00:00Z",
        ),
        McpServer(
            name="slack-mcp",
            slug="slack-mcp",
            description="Read and send Slack messages, search channels",
            repo_url="https://github.com/modelcontextprotocol/slack-server",
            stars=2800,
            forks=210,
            watchers=65,
            open_issues=42,
            language="TypeScript",
            topics=["slack", "mcp", "messaging", "collaboration"],
            readme_snippet="Slack MCP server for reading channels, searching messages, and sending notifications",
            last_push="2026-05-25T11:00:00Z",
            created_at="2025-04-01T00:00:00Z",
        ),
        McpServer(
            name="notion-mcp",
            slug="notion-mcp",
            description="Manage Notion pages, databases, and blocks via MCP",
            repo_url="https://github.com/modelcontextprotocol/notion-server",
            stars=5200,
            forks=480,
            watchers=140,
            open_issues=55,
            language="TypeScript",
            topics=["notion", "mcp", "productivity", "knowledge-base"],
            readme_snippet="Notion MCP server for creating, querying, and updating pages and databases",
            last_push="2026-05-26T08:00:00Z",
            created_at="2025-01-20T00:00:00Z",
        ),
        McpServer(
            name="brave-search-mcp",
            slug="brave-search-mcp",
            description="Web search via Brave Search API for AI agents",
            repo_url="https://github.com/modelcontextprotocol/brave-search-server",
            stars=1900,
            forks=150,
            watchers=40,
            open_issues=18,
            language="TypeScript",
            topics=["search", "brave", "mcp", "web"],
            readme_snippet="Brave Search MCP server providing web search capabilities to AI agents",
            last_push="2026-05-15T10:00:00Z",
            created_at="2025-05-01T00:00:00Z",
        ),
        McpServer(
            name="puppeteer-mcp",
            slug="puppeteer-mcp",
            description="Browser automation and web scraping for AI agents",
            repo_url="https://github.com/modelcontextprotocol/puppeteer-server",
            stars=6700,
            forks=520,
            watchers=160,
            open_issues=62,
            language="TypeScript",
            topics=["puppeteer", "mcp", "browser", "automation"],
            readme_snippet="Puppeteer MCP server for browser automation, screenshots, and web interaction",
            last_push="2026-05-29T18:00:00Z",
            created_at="2025-02-01T00:00:00Z",
        ),
        McpServer(
            name="redis-mcp",
            slug="redis-mcp",
            description="Cache, queue, and pub/sub operations via Redis MCP",
            repo_url="https://github.com/modelcontextprotocol/redis-server",
            stars=1500,
            forks=120,
            watchers=35,
            open_issues=15,
            language="Python",
            topics=["redis", "mcp", "cache", "infrastructure"],
            readme_snippet="Redis MCP server for cache operations, pub/sub, and queue management",
            last_push="2026-05-10T14:00:00Z",
            created_at="2025-06-01T00:00:00Z",
        ),
        McpServer(
            name="sentry-mcp",
            slug="sentry-mcp",
            description="Query Sentry errors, issues, and performance data",
            repo_url="https://github.com/modelcontextprotocol/sentry-server",
            stars=2100,
            forks=180,
            watchers=55,
            open_issues=22,
            language="TypeScript",
            topics=["sentry", "mcp", "monitoring", "errors"],
            readme_snippet="Sentry MCP server for querying application errors, performance metrics, and issues",
            last_push="2026-05-22T12:00:00Z",
            created_at="2025-03-15T00:00:00Z",
        ),
    ]
    for s in seeds:
        store.upsert(s)
