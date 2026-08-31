import json
from datetime import datetime, timezone

from capalarm.cli import build_parser, main, _parse_ts, _read_records, _samples_from_records


def test_parse_ts_utc_default():
    dt = _parse_ts("2026-08-01T12:00:00")
    assert dt.tzinfo is not None and dt.utcoffset().total_seconds() == 0


def test_parse_ts_z_suffix():
    dt = _parse_ts("2026-08-01T12:00:00Z")
    assert dt.tzinfo is not None


def test_read_records_json_list(tmp_path):
    p = tmp_path / "u.json"
    p.write_text(json.dumps([{"provider": "a", "tokens": 5}]))
    with open(p) as fh:
        assert _read_records(fh, "json") == [{"provider": "a", "tokens": 5}]


def test_sample_missing_provider_raises(tmp_path):
    p = tmp_path / "u.json"
    p.write_text(json.dumps([{"tokens": 5}]))
    with open(p) as fh:
        records = _read_records(fh, "json")
    try:
        _samples_from_records(records)
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_samples_from_records_provider_ts_tokens():
    records = [{"provider": "anthropic", "timestamp": "2026-08-01T00:00:00Z", "tokens": "100"}]
    samples = _samples_from_records(records)
    assert samples[0].provider == "anthropic"
    assert samples[0].tokens == 100
    assert isinstance(samples[0].timestamp, datetime)


def test_parser_flags():
    p = build_parser()
    ns = p.parse_args(["--provider", "anthropic", "--json", "--plan", "x"])
    assert ns.provider == "anthropic"
    assert ns.json is True
    assert ns.plan == "x"


def test_main_json_stdin_roundtrip():
    import io, sys
    data = json.dumps([{"provider": "anthropic", "timestamp": "2026-08-01T00:00:00Z", "tokens": 100}])
    old_stdin = sys.stdin
    sys.stdin = io.StringIO(data)
    try:
        rc = main(["--json"])
    finally:
        sys.stdin = old_stdin
    assert rc == 0
    # output is printed to stdout; we only assert exit code here


def test_main_parse_error_returns_2(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("not json")
    assert main([str(p), "--json"]) == 2


def test_main_missing_file_returns_2(tmp_path):
    assert main([str(tmp_path / "nope.json"), "--json"]) == 2