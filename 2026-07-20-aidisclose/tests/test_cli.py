"""CLI tests: list / analyze / check exit codes and output."""
import json
from contextlib import redirect_stdout
from io import StringIO

from aidisclose.cli import main

from fixtures import make_profile


def _run(argv):
    buf = StringIO()
    with redirect_stdout(buf):
        rc = main(argv)
    return rc, buf.getvalue()


def test_list_returns_rows():
    rc, out = _run(["list"])
    assert rc == 0
    assert "nyc-ll144" in out
    assert "eu-aiact-13" in out


def test_list_status_filter():
    rc, out = _run(["list", "--status", "proposed"])
    assert rc == 0
    assert "nyc-listing-ai" in out
    assert "nyc-ll144" not in out   # in_force, filtered out


def test_analyze_json_flags():
    rc, out = _run([
        "analyze", "--name", "CliCo", "--jurisdictions", "US-NY",
        "--sectors", "employment", "--ai_uses", "hiring", "--format", "json"])
    assert rc == 0
    data = json.loads(out)
    assert data["score"] == 100.0
    assert data["blocking"] is True


def test_check_blocks_on_critical_gap():
    rc, _ = _run([
        "check", "--name", "CliCo", "--jurisdictions", "US-NY",
        "--sectors", "employment", "--ai_uses", "hiring"])
    assert rc == 1


def test_check_passes_when_implemented(tmp_path):
    prof = tmp_path / "org.json"
    prof.write_text(json.dumps({
        "name": "GoodCo",
        "jurisdictions": ["US-NY"],
        "sectors": ["employment"],
        "ai_uses": ["hiring"],
        "implemented": ["bias_audit", "candidate_disclosure",
                        "summary_results", "record_keeping"],
    }), encoding="utf-8")
    rc, out = _run(["check", "--profile", str(prof), "--format", "json"])
    assert rc == 0
    # JSON report should show no blocking gaps
    assert json.loads(out)["blocking"] is False


def test_analyze_profile_file(tmp_path):
    prof = tmp_path / "org.json"
    prof.write_text(json.dumps({
        "name": "FileCo",
        "jurisdictions": ["US-IL"],
        "ai_uses": ["biometric"],
    }), encoding="utf-8")
    rc, out = _run(["analyze", "--profile", str(prof), "--format", "json"])
    assert rc == 0
    data = json.loads(out)
    assert data["profile"] == "FileCo"
    # il-bipa applies with a critical unmet consent obligation
    assert data["blocking"] is True
