import json
import subprocess
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path

from fixtures import good_spec, bad_spec


def _write_spec(path: Path, spec) -> None:
    path.write_text(json.dumps(asdict(spec)), encoding="utf-8")


def _run(args):
    return subprocess.run(
        [sys.executable, "-m", "mcpshield", *args],
        capture_output=True, text=True,
    )


def test_cli_good_passes():
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "good.json"
        _write_spec(p, good_spec())
        r = _run(["check", str(p)])
    assert r.returncode == 0, r.stderr
    assert "PASS" in r.stdout


def test_cli_bad_fails_exit1():
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "bad.json"
        _write_spec(p, bad_spec())
        r = _run(["check", str(p)])
    assert r.returncode == 1, r.stdout
    assert "FAIL" in r.stdout
    assert "CRITICAL" in r.stdout


def test_cli_json_output():
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "bad.json"
        _write_spec(p, bad_spec())
        r = _run(["check", str(p), "--json"])
    assert r.returncode == 1
    data = json.loads(r.stdout)
    assert data["band"] == "FAIL"


def test_cli_dir_batch():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        _write_spec(td / "a.json", good_spec())
        _write_spec(td / "b.json", bad_spec())
        r = _run(["check", "--dir", str(td)])
    # bad one fails -> exit 1
    assert r.returncode == 1
    assert "good-docs-fetcher" in r.stdout
    assert "evil-gateway" in r.stdout


def test_cli_version():
    r = _run(["version"])
    assert r.returncode == 0
    assert r.stdout.strip() == "0.1.0"
