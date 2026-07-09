"""Shared test fixtures: offline local breach source (no network)."""

import json
import tempfile
from pathlib import Path

import pytest

from breach_sentinel.models import Identity
from breach_sentinel.sources import LocalSource

SAMPLE = [
    {"identity_value": "alice@example.com", "breach_type": "email", "breach_name": "Adobe 2013", "breach_date": "2013-10-04"},
    {"identity_value": "alice@example.com", "breach_type": "password", "breach_name": "Collection #1", "breach_date": "2019-01-01"},
    {"identity_value": "carol@bank.com", "breach_type": "ssn", "breach_name": "Nefos Puffpal 2026", "breach_date": "2026-06-29"},
    {"identity_value": "carol@bank.com", "breach_type": "passport", "breach_name": "Nefos Puffpal 2026", "breach_date": "2026-06-29"},
]


@pytest.fixture
def sample_path(tmp_path: Path) -> str:
    p = tmp_path / "breaches.json"
    p.write_text(json.dumps(SAMPLE), encoding="utf-8")
    return str(p)


@pytest.fixture
def local_source(sample_path: str) -> LocalSource:
    return LocalSource(sid="local:test", path=sample_path, name="Test Local")


@pytest.fixture
def alice() -> Identity:
    return Identity(iid="alice", label="Alice", email="alice@example.com")


@pytest.fixture
def carol() -> Identity:
    return Identity(iid="carol", label="Carol", email="carol@bank.com", ssn="123-45-6789", passport="X1234567")


@pytest.fixture
def clean_db(tmp_path: Path) -> str:
    return str(tmp_path / "test_sentinel.db")
