"""Tests for the reader-facing badge spec + CLI smoke tests."""
import json
import subprocess
import sys

from contentmark import badge_html, badge_css, badge_script, band_label
from contentmark.models import Provenance, ProvenanceLabel

from fixtures import AI_TEXT, HUMAN_TEXT, PLAIN_TEXT

PKG = "contentmark"
PY = sys.executable


def _prov():
    return Provenance(rid="cm_badge1", label=ProvenanceLabel.AI_GENERATED, tool="AcmeWriter", author="alice")


def test_badge_html_contains_label():
    html = badge_html(_prov())
    assert "AI-generated" in html
    assert "data-cm-rid" in html
    assert "cm-badge--ai_generated" in html


def test_badge_css_has_classes():
    css = badge_css()
    assert ".cm-badge--ai_generated" in css
    assert ".cm-badge--human" in css


def test_badge_script_self_contained():
    js = badge_script()
    assert "ContentMark" in js
    assert "querySelectorAll" in js


def test_band_label_mapping():
    assert band_label("likely_ai").startswith("Likely")


def test_cli_detect_ai_exit1():
    proc = subprocess.run(
        [PY, "-m", PKG, "detect", "-", "--json"],
        input=AI_TEXT, capture_output=True, text=True,
    )
    assert proc.returncode == 1
    data = json.loads(proc.stdout)
    assert data["band"] in ("likely_ai", "very_likely_ai")


def test_cli_detect_human_exit0():
    proc = subprocess.run(
        [PY, "-m", PKG, "detect", "-"],
        input=HUMAN_TEXT, capture_output=True, text=True,
    )
    assert proc.returncode == 0


def test_cli_label_verify_roundtrip():
    labeled = subprocess.run(
        [PY, "-m", PKG, "label", "-", "--label", "ai_generated", "--tool", "Acme"],
        input=PLAIN_TEXT, capture_output=True, text=True,
    ).stdout
    assert "contentmark:provenance" in labeled
    v = subprocess.run(
        [PY, "-m", PKG, "verify", "-", "--json"],
        input=labeled, capture_output=True, text=True,
    )
    data = json.loads(v.stdout)
    assert data["present"] and data["valid"] and not data["tampered"]


def test_cli_badge_emits_html():
    proc = subprocess.run(
        [PY, "-m", PKG, "badge", "--label", "ai_assisted", "--part", "html"],
        capture_output=True, text=True,
    )
    assert "cm-badge--ai_assisted" in proc.stdout
