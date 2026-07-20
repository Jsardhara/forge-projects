"""Report formatting tests."""
import json

from aidisclose.engine import analyze
from aidisclose.report import to_json, to_markdown

from fixtures import make_profile


def _report():
    p = make_profile(name="ReportCo", jurisdictions=["US-NY"],
                     sectors=["employment"], ai_uses=["hiring"])
    return analyze(p)


def test_markdown_contains_title_and_gap():
    md = to_markdown(_report())
    assert "# AI-Disclosure Compliance Report: ReportCo" in md
    assert "Risk band" in md
    assert "Unmet obligations" in md
    assert "nyc-ll144" in md or "NYC Local Law 144" in md


def test_json_roundtrip():
    r = _report()
    data = json.loads(to_json(r))
    assert data["profile"] == "ReportCo"
    assert data["score"] == 100.0
    assert data["blocking"] is True
    assert data["applicable_count"] >= 1
    assert "applicable" in data and "monitored" in data
    # reference_date serialized as ISO string
    assert data["reference_date"] == "2026-07-20"


def test_no_applicable_still_renders():
    p = make_profile(name="CleanCo", jurisdictions=["US-NY"],
                     sectors=["real_estate"], ai_uses=["hiring"])
    r = analyze(p)
    md = to_markdown(r)
    assert "No applicable mandates" in md
