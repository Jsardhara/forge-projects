from mcpshield.models import MCPServerSpec, ToolSpec, Report, SEVERITY_WEIGHT
from fixtures import good_spec, bad_spec


def test_spec_from_dict_defaults():
    spec = MCPServerSpec.from_dict({"name": "x"})
    assert spec.name == "x"
    assert spec.transport == "stdio"
    assert spec.tools == ()
    assert spec.egress == ()
    assert spec.secrets == ()


def test_tool_spec_frozen():
    t = ToolSpec(name="a")
    try:
        t.name = "b"  # type: ignore[misc]
    except Exception:
        pass
    else:
        raise AssertionError("ToolSpec should be frozen")


def test_good_spec_passes():
    report = __import__("mcpshield").analyze(good_spec())
    assert report.band == "PASS"
    assert report.risk_score == 0
    assert report.passed
    assert not report.failed
    # At most INFO-level (transport stdio) findings, never CRITICAL/HIGH
    assert all(f.severity in ("INFO",) for f in report.findings)


def test_bad_spec_fails():
    report = __import__("mcpshield").analyze(bad_spec())
    assert report.band == "FAIL"
    assert report.failed
    assert any(f.severity == "CRITICAL" for f in report.findings)


def test_report_to_dict_roundtrip():
    report = __import__("mcpshield").analyze(bad_spec())
    d = report.to_dict()
    assert d["server"] == "evil-gateway"
    assert d["band"] == "FAIL"
    assert isinstance(d["risk_score"], int)
    assert len(d["findings"]) == len(report.findings)
    # generated_at is ISO string
    assert "T" in d["generated_at"]


def test_severity_weights_defined():
    for sev in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"):
        assert sev in SEVERITY_WEIGHT
