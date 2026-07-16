import json
from tokenaudit.cli import run_cli
from fixtures import claude_line, assistant_text, tool_use_read, tool_result, generic_line


def _write_claude(path, preread=5000, tool_in=2000, tool_out=100, result_in=3000):
    text = "\n".join([
        claude_line("user", {"input_tokens": preread, "output_tokens": 0}, content=[{"type": "text", "text": "system"}]),
        claude_line("assistant", {"input_tokens": tool_in, "output_tokens": tool_out}, model="claude-sonnet-4", content=tool_use_read("a.py")),
        claude_line("user", {"input_tokens": result_in, "output_tokens": 0}, content=tool_result("big result here")),
        claude_line("assistant", {"input_tokens": 500, "output_tokens": 50}, model="claude-sonnet-4", content=assistant_text("done")),
    ]) + "\n"
    path.write_text(text, encoding="utf-8")


def test_cli_profile_md(tmp_path, capsys):
    p = tmp_path / "a.jsonl"
    _write_claude(p)
    rc = run_cli(["profile", str(p)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "# Token Audit" in out
    assert "Pre-read (before 1st tool)" in out


def test_cli_profile_json(tmp_path, capsys):
    p = tmp_path / "a.jsonl"
    _write_claude(p)
    rc = run_cli(["profile", str(p), "--format", "json"])
    assert rc == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["agent"] == "claude-code"
    assert data["total_input"] > 0


def test_cli_compare(tmp_path, capsys):
    a = tmp_path / "a.jsonl"
    b = tmp_path / "b.jsonl"
    _write_claude(a, preread=5000)
    _write_claude(b, preread=30000)  # much higher pre-read
    rc = run_cli(["compare", str(a), str(b)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Token Audit: Compare" in out
    assert "a.jsonl" in out and "b.jsonl" in out


def test_cli_report_dir(tmp_path, capsys):
    d = tmp_path / "sessions"
    d.mkdir()
    _write_claude(d / "one.jsonl")
    _write_claude(d / "two.jsonl", preread=20000)
    rc = run_cli(["report", str(d)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "one.jsonl" in out and "two.jsonl" in out


def test_cli_report_empty_dir(tmp_path, capsys):
    d = tmp_path / "empty"
    d.mkdir()
    rc = run_cli(["report", str(d)])
    assert rc == 1
