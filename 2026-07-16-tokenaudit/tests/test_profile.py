from tokenaudit.models import Message, Session, Usage
from tokenaudit.profile import phase_breakdown, file_reads, waste_findings


def _msg(role, inp, out, tool_use=False, tool_result=False, reads=(),
         model="claude-sonnet-4", content=None):
    return Message(
        role=role,
        usage=Usage(input_tokens=inp, output_tokens=out),
        model=model,
        has_tool_use=tool_use,
        has_tool_result=tool_result,
        file_reads=reads,
        content=content,
    )


def test_phase_breakdown_classification():
    sess = Session(source="s", messages=[
        _msg("user", 5000, 0),
        _msg("assistant", 2000, 100, tool_use=True, reads=("a.py",)),
        _msg("user", 3000, 0, tool_result=True, content=[{"type": "tool_result", "content": "r"}]),
        _msg("assistant", 500, 50),
    ])
    ph = phase_breakdown(sess)
    assert ph.preread_input == 7000
    assert ph.tool_result_input == 3000
    assert ph.other_input == 500
    assert ph.generation_output == 150


def test_file_reads_aggregate():
    sess = Session(source="s", messages=[
        _msg("assistant", 4000, 10, tool_use=True, reads=("a.py",)),
    ])
    frs = file_reads(sess)
    assert len(frs) == 1
    assert frs[0].path == "a.py"
    assert frs[0].read_count == 1
    assert frs[0].est_input_tokens == 4000


def test_preread_warn_vs_high():
    # WARN range
    sess = Session(source="s", messages=[
        _msg("user", 5000, 0),
        _msg("assistant", 2000, 100, tool_use=True, reads=("a.py",)),
    ])
    kinds = {f.kind: f.severity for f in waste_findings(sess)}
    assert kinds.get("PRE_READ_OVERHEAD") == "WARN"

    # HIGH range
    sess2 = Session(source="s", messages=[
        _msg("user", 9000, 0),
        _msg("assistant", 1000, 100, tool_use=True, reads=("a.py",)),
    ])
    kinds2 = {f.kind: f.severity for f in waste_findings(sess2)}
    assert kinds2.get("PRE_READ_OVERHEAD") == "HIGH"


def test_no_preread_finding_when_small():
    sess = Session(source="s", messages=[
        _msg("user", 100, 0),
        _msg("assistant", 200, 10, tool_use=True, reads=("a.py",)),
    ])
    findings = waste_findings(sess)
    assert not any(f.kind == "PRE_READ_OVERHEAD" for f in findings)


def test_redundant_reads_finding():
    sess = Session(source="s", messages=[
        _msg("user", 100, 0),
        _msg("assistant", 200, 10, tool_use=True, reads=("a.py",)),
        _msg("assistant", 5000, 10, tool_use=True, reads=("a.py",)),
    ])
    findings = waste_findings(sess)
    red = [f for f in findings if f.kind == "REDUNDANT_READS"]
    assert red, "expected REDUNDANT_READS finding"
    assert red[0].wasted_tokens > 0


def test_telemetry_overhead_finding():
    big = "x" * 600
    sess = Session(source="s", messages=[
        _msg("user", 100, 0),
        _msg("assistant", 100, 50),
        _msg("user", 2000, 0, tool_result=True, content=[{"type": "tool_result", "content": big}]),
        _msg("user", 2000, 0, tool_result=True, content=[{"type": "tool_result", "content": big}]),
        _msg("user", 2000, 0, tool_result=True, content=[{"type": "tool_result", "content": big}]),
    ])
    findings = waste_findings(sess)
    tel = [f for f in findings if f.kind == "TELEMETRY_OVERHEAD"]
    assert tel, "expected TELEMETRY_OVERHEAD finding"
    assert tel[0].wasted_tokens > 0


def test_context_bloat_finding():
    sess = Session(source="s", messages=[
        _msg("user", 120000, 0),
        _msg("assistant", 0, 1000),
    ])
    kinds = {f.kind for f in waste_findings(sess)}
    assert "CONTEXT_BLOAT" in kinds
