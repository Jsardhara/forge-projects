"""Tests for AI Failbook models and storage."""

import pytest
from ai_failbook.models import (
    Category,
    FailureMode,
    FailureModeCreate,
    FailureModeUpdate,
    SearchQuery,
    Severity,
)
from ai_failbook.store import Store


@pytest.fixture
def store():
    """Create a fresh in-memory store for each test."""
    s = Store(":memory:")
    yield s
    s.close()


@pytest.fixture
def sample_data():
    """Sample failure mode create data."""
    return FailureModeCreate(
        title="Test Hallucination",
        description="Model generated fake citations for a research paper",
        severity=Severity.HIGH,
        category=Category.HALLUCINATION,
        model="gpt-4",
        expected_behavior="Should have said it doesn't know",
        actual_behavior="Generated 5 fake paper titles with plausible authors",
        workaround="Use RAG with verified sources",
        tags=["hallucination", "citations", "research"],
    )


class TestModels:
    def test_failure_mode_create(self, sample_data):
        assert sample_data.title == "Test Hallucination"
        assert sample_data.severity == Severity.HIGH
        assert sample_data.category == Category.HALLUCINATION

    def test_failure_mode_default_vid(self):
        fm = FailureMode(title="Test", description="A test failure mode")
        assert len(fm.vid) == 8
        assert fm.upvotes == 0
        assert fm.verified is False

    def test_severity_enum(self):
        assert Severity.LOW.value == "low"
        assert Severity.CRITICAL.value == "critical"

    def test_category_enum(self):
        assert Category.HALLUCINATION.value == "hallucination"
        assert Category.PROMPT_INJECTION.value == "prompt_injection"

    def test_search_query_defaults(self):
        q = SearchQuery()
        assert q.limit == 20
        assert q.offset == 0
        assert q.verified_only is False


class TestStore:
    def test_create_and_get(self, store, sample_data):
        fm = store.create(sample_data)
        assert fm.vid is not None
        assert fm.title == "Test Hallucination"

        retrieved = store.get(fm.vid)
        assert retrieved is not None
        assert retrieved.title == fm.title
        assert retrieved.severity == Severity.HIGH

    def test_get_nonexistent(self, store):
        assert store.get("nonexistent") is None

    def test_update(self, store, sample_data):
        fm = store.create(sample_data)
        updated = store.update(fm.vid, FailureModeUpdate(title="Updated Title"))
        assert updated is not None
        assert updated.title == "Updated Title"
        assert updated.description == fm.description  # unchanged

    def test_update_nonexistent(self, store):
        result = store.update("nonexistent", FailureModeUpdate(title="Nope"))
        assert result is None

    def test_delete(self, store, sample_data):
        fm = store.create(sample_data)
        assert store.delete(fm.vid) is True
        assert store.get(fm.vid) is None

    def test_delete_nonexistent(self, store):
        assert store.delete("nonexistent") is False

    def test_upvote(self, store, sample_data):
        fm = store.create(sample_data)
        assert fm.upvotes == 0
        updated = store.upvote(fm.vid)
        assert updated is not None
        assert updated.upvotes == 1

    def test_upvote_nonexistent(self, store):
        assert store.upvote("nonexistent") is None

    def test_search_by_text(self, store, sample_data):
        store.create(sample_data)
        result = store.search(SearchQuery(q="hallucination"))
        assert result.total >= 1
        assert any("hallucination" in fm.title.lower() or "hallucination" in fm.description.lower() for fm in result.items)

    def test_search_by_category(self, store, sample_data):
        store.create(sample_data)
        result = store.search(SearchQuery(category=Category.HALLUCINATION))
        assert result.total >= 1
        for fm in result.items:
            assert fm.category == Category.HALLUCINATION

    def test_search_by_severity(self, store, sample_data):
        store.create(sample_data)
        result = store.search(SearchQuery(severity=Severity.HIGH))
        assert result.total >= 1
        for fm in result.items:
            assert fm.severity == Severity.HIGH

    def test_search_by_tag(self, store, sample_data):
        store.create(sample_data)
        result = store.search(SearchQuery(tag="citations"))
        assert result.total >= 1

    def test_search_empty(self, store):
        result = store.search(SearchQuery())
        assert result.total == 0
        assert result.items == []

    def test_search_pagination(self, store):
        for i in range(5):
            store.create(FailureModeCreate(
                title=f"Failure {i}",
                description=f"Description for failure {i}",
            ))
        result = store.search(SearchQuery(limit=2, offset=0))
        assert result.total == 5
        assert len(result.items) == 2

    def test_stats(self, store, sample_data):
        store.create(sample_data)
        stats = store.stats()
        assert stats.total_entries >= 1
        assert "high" in stats.by_severity
        assert "hallucination" in stats.by_category
        assert stats.verified_count == 0

    def test_stats_verified(self, store, sample_data):
        fm = store.create(sample_data)
        store.update(fm.vid, FailureModeUpdate(verified=True))
        stats = store.stats()
        assert stats.verified_count >= 1

    def test_seed_sample_data(self, store):
        fms = store.seed_sample_data()
        assert len(fms) >= 5
        stats = store.stats()
        assert stats.total_entries >= 5

    def test_search_verified_only(self, store, sample_data):
        fm = store.create(sample_data)
        store.update(fm.vid, FailureModeUpdate(verified=True))
        result = store.search(SearchQuery(verified_only=True))
        assert result.total >= 1
        for fm in result.items:
            assert fm.verified is True

    def test_search_by_model(self, store, sample_data):
        store.create(sample_data)
        result = store.search(SearchQuery(model="gpt-4"))
        assert result.total >= 1

    def test_multiple_entries(self, store):
        titles = ["Alpha", "Beta", "Gamma", "Delta", "Epsilon"]
        for t in titles:
            store.create(FailureModeCreate(
                title=t,
                description=f"Description for {t}",
            ))
        result = store.search(SearchQuery())
        assert result.total == 5


class TestStoreEdgeCases:
    def test_create_minimal(self, store):
        fm = store.create(FailureModeCreate(
            title="Minimal",
            description="Minimal description",
        ))
        assert fm.severity == Severity.MEDIUM
        assert fm.category == Category.OTHER
        assert fm.tags == []

    def test_update_no_changes(self, store, sample_data):
        fm = store.create(sample_data)
        updated = store.update(fm.vid, FailureModeUpdate())
        assert updated is not None
        assert updated.title == fm.title

    def test_tags_preserved(self, store, sample_data):
        fm = store.create(sample_data)
        retrieved = store.get(fm.vid)
        assert retrieved is not None
        assert set(retrieved.tags) == {"hallucination", "citations", "research"}
