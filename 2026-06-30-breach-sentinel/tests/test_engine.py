"""End-to-end engine + CLI smoke tests (offline, via LocalSource)."""

import json
import subprocess
import sys
from pathlib import Path

from breach_sentinel.engine import SentinelEngine
from breach_sentinel.models import Severity
from breach_sentinel.sources import LocalSource

PKG = Path(__file__).resolve().parents[1] / "src"


def test_engine_scan_alice(local_source, alice, clean_db):
    from breach_sentinel.store import SentinelStore
    store = SentinelStore(clean_db)
    engine = SentinelEngine([local_source], store=store)
    result = engine.scan_identity(alice)
    assert result.score.record_count == 2  # email + password for alice
    assert result.score.severity.rank >= 1


def test_engine_scan_carol_critical(local_source, carol, clean_db):
    from breach_sentinel.store import SentinelStore
    store = SentinelStore(clean_db)
    engine = SentinelEngine([local_source], store=store)
    result = engine.scan_identity(carol)
    assert result.score.severity.rank >= Severity.CRITICAL.rank  # noqa: F821
    assert len(result.alerts) >= 1


def test_cli_scan_json_exit_code(tmp_path, sample_path):
    db = tmp_path / "cli.db"
    cmd = [
        sys.executable, "-m", "breach_sentinel",
        "--db", str(db), "scan",
        "--label", "Alice", "--email", "alice@example.com",
        "--local", sample_path, "--json",
    ]
    env = dict(__import__("os").environ)
    env.pop("HIBP_API_KEY", None)
    out = subprocess.run(cmd, capture_output=True, text=True, cwd=PKG.parent.parent, env=env)
    assert out.returncode == 1  # alerts fired -> non-zero for CI
    data = json.loads(out.stdout)
    assert data["record_count"] == 2
    assert data["score"] > 0


def test_cli_no_sources_errors(tmp_path):
    db = tmp_path / "cli2.db"
    env = dict(__import__("os").environ)
    env.pop("HIBP_API_KEY", None)
    cmd = [
        sys.executable, "-m", "breach_sentinel", "--db", str(db),
        "scan", "--label", "NoSrc", "--email", "x@y.com",
    ]
    out = subprocess.run(cmd, capture_output=True, text=True, cwd=PKG.parent.parent, env=env)
    assert out.returncode == 2
