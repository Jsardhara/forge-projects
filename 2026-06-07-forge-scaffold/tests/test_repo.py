"""Tests for forge_scaffold.repo."""

import tempfile
from pathlib import Path

import pytest

from forge_scaffold.repo import (
    scan_projects,
    read_index,
    update_index,
    get_project_count,
    get_last_project,
)


@pytest.fixture
def mock_repo(tmp_path):
    """Create a mock forge-projects repo structure."""
    (tmp_path / "2026-06-05-test-alpha").mkdir()
    (tmp_path / "2026-06-05-test-alpha" / "README.md").write_text("# Test Alpha\n\nDesc")
    (tmp_path / "2026-06-06-test-beta").mkdir()
    (tmp_path / "2026-06-06-test-beta" / "README.md").write_text("# Test Beta\n\nDesc")
    (tmp_path / ".git").mkdir()  # should be ignored
    (tmp_path / "INDEX.md").write_text("# old index")  # should be ignored
    return tmp_path


class TestScanProjects:
    def test_scans_correct_folders(self, mock_repo):
        projects = scan_projects(mock_repo)
        assert len(projects) == 2

    def test_extracts_metadata(self, mock_repo):
        projects = scan_projects(mock_repo)
        assert projects[0]["slug"] == "test-alpha"
        assert projects[0]["date"] == "2026-06-05"
        assert projects[1]["slug"] == "test-beta"

    def test_ignores_non_project_dirs(self, mock_repo):
        projects = scan_projects(mock_repo)
        slugs = [p["slug"] for p in projects]
        assert ".git" not in slugs
        assert "INDEX.md" not in slugs


class TestUpdateIndex:
    def test_rebuilds_index(self, mock_repo):
        content = update_index(mock_repo)
        assert "test-alpha" in content
        assert "test-beta" in content
        assert "2026-06-05" in content
        assert "2026-06-06" in content

    def test_writes_to_disk(self, mock_repo):
        update_index(mock_repo)
        index_path = mock_repo / "INDEX.md"
        assert index_path.exists()
        content = index_path.read_text()
        assert "test-alpha" in content


class TestGetProjectCount:
    def test_counts_correctly(self, mock_repo):
        assert get_project_count(mock_repo) == 2


class TestGetLastProject:
    def test_returns_last(self, mock_repo):
        last = get_last_project(mock_repo)
        assert last is not None
        assert last["slug"] == "test-beta"
