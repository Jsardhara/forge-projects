"""Tests for the darkwatch CLI (uses subprocess against the installed entry point)."""
from __future__ import annotations

import sys
from pathlib import Path
from subprocess import PIPE, run

PYTHON = sys.executable
ROOT = Path(__file__).resolve().parent.parent
PKG = "darkwatch"

HEAVY = """
<button>Start your free trial</button>
<p>Your subscription renews automatically.</p>
<p>Only 2 seats left! Hurry!</p>
<div class="countdown">x</div>
<label><input type="checkbox" name="marketing" checked> Subscribe</label>
<p>When you unsubscribe you will be charged a fee.</p>
"""

CLEAN = """
<form><label><input type="checkbox" name="news"> Subscribe</label></form>
<a href="/account/cancel">cancel</a>
"""


def _run(args, stdin=None):
    return run(
        [PYTHON, "-m", PKG, *args],
        input=stdin, capture_output=True, text=True, cwd=str(ROOT),
    )


def test_cli_scan_non_compliant_exit_code():
    r = _run(["scan", "-", "--format", "text"], stdin=HEAVY)
    assert r.returncode == 1, r.stderr
    assert "NON-COMPLIANT" in r.stdout or "non_compliant" in r.stdout.lower()


def test_cli_scan_clean_exit_zero():
    r = _run(["scan", "-", "--format", "text"], stdin=CLEAN)
    assert r.returncode == 0, r.stderr
    assert "COMPLIANT" in r.stdout


def test_cli_scan_json():
    r = _run(["scan", "-", "--format", "json"], stdin=HEAVY)
    assert r.returncode == 1, r.stderr
    assert '"band"' in r.stdout and "NON_COMPLIANT" in r.stdout


def test_cli_checklist():
    r = _run(["checklist", "-"], stdin=HEAVY)
    assert r.returncode == 1, r.stderr
    assert "NYC Local Law" in r.stdout
    assert "[XX]" in r.stdout  # at least one fail


def test_cli_rules_lists_eight():
    r = _run(["rules"])
    assert r.returncode == 0, r.stderr
    # 8 rule ids printed
    lines = [ln for ln in r.stdout.splitlines() if ln.strip()]
    assert len(lines) == 8


def test_cli_report_to_stdout():
    r = _run(["report", "-"], stdin=HEAVY)
    assert r.returncode == 1, r.stderr
    assert "## Findings" in r.stdout or "## Regulation checklist" in r.stdout
