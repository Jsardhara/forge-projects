from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from exfilsentinel.cli import main

UTC = timezone.utc


def _write_events(path, events):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(events, fh)


def test_cli_scan_exfil(tmp_path):
    p = tmp_path / "events.json"
    base = datetime(2026, 7, 11, 12, 0, 0, tzinfo=UTC)
    events = [
        {"actor_id": "mallory", "model": "ft:secret-weights", "timestamp": (base + timedelta(minutes=i)).isoformat(), "prompt_tokens": 10, "completion_tokens": 5_000_000}
        for i in range(3)
    ]
    _write_events(p, events)
    rc = main(["scan", "--events", str(p), "--actor", "mallory"])
    assert rc == 1  # exfiltration -> non-zero exit (CI gate)


def test_cli_scan_benign(tmp_path):
    p = tmp_path / "events.json"
    base = datetime(2026, 7, 11, 12, 0, 0, tzinfo=UTC)
    events = [
        {"actor_id": "alice", "model": "gpt-4", "timestamp": (base + timedelta(minutes=i)).isoformat(), "prompt_tokens": 500, "completion_tokens": 400}
        for i in range(5)
    ]
    _write_events(p, events)
    rc = main(["scan", "--events", str(p), "--actor", "alice"])
    assert rc == 0


def test_cli_embed_verify(tmp_path):
    out = tmp_path / "wm.txt"
    rc = main(["embed", "--text", "confidential output", "--org", "acme", "--model", "ft:acme", "--out", str(out)])
    assert rc == 0
    rc2 = main(["verify", "--text-file", str(out)])
    assert rc2 == 0


def test_cli_detect(tmp_path):
    from exfilsentinel.watermark import embed
    from exfilsentinel.models import ProvenanceRecord
    wm = embed("x", ProvenanceRecord("o", "m", datetime(2026,7,11,tzinfo=UTC), "n"))
    f = tmp_path / "w.txt"
    f.write_text(wm.text, encoding="utf-8")
    assert main(["detect", "--text-file", str(f)]) == 0
    assert main(["detect", "--text", "plain text no wm"]) == 1
