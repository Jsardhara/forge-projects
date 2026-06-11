"""Tests for npm-shield report module."""
import json
from io import StringIO

import pytest
from rich.console import Console

from npm_shield.scanner import PackageScriptInfo, ScanResult
from npm_shield.report import render_report, render_json


@pytest.fixture
def scripted_result():
    affected = [
        PackageScriptInfo(
            name="esbuild", version="0.21.0",
            scripts={"postinstall": "node install.js", "preinstall": "node check.js"},
            resolved="https://registry.npmjs.org/esbuild/-/esbuild-0.21.0.tgz",
        ),
        PackageScriptInfo(
            name="husky", version="8.3.7",
            scripts={"install": "node husky.js"},
            resolved="https://registry.npmjs.org/husky/-/husky-8.3.7.tgz",
        ),
    ]
    return ScanResult(
        project_name="test-proj",
        project_version="1.0.0",
        lockfile_version=3,
        total_packages=10,
        packages_with_scripts=affected,
        scan_path="/tmp/test",
    )


@pytest.fixture
def clean_result():
    return ScanResult(
        project_name="clean-proj",
        project_version="2.0.0",
        lockfile_version=3,
        total_packages=5,
        packages_with_scripts=[],
        scan_path="/tmp/clean",
    )


class TestRenderReport:
    def test_runs_without_error(self, scripted_result):
        buf = StringIO()
        console = Console(file=buf, force_terminal=True, width=120)
        render_report(scripted_result, console=console)
        output = buf.getvalue()
        assert "npm-shield" in output
        assert "esbuild" in output
        assert "HIGH" in output

    def test_clean_project_message(self, clean_result):
        buf = StringIO()
        console = Console(file=buf, force_terminal=True, width=120)
        render_report(clean_result, console=console)
        output = buf.getvalue()
        assert "No install scripts found" in output or "v12 ready" in output


class TestRenderJson:
    def test_valid_json(self, scripted_result):
        output = render_json(scripted_result)
        parsed = json.loads(output)
        assert parsed["project"]["name"] == "test-proj"
        assert parsed["total_packages"] == 10
        assert len(parsed["packages_with_scripts"]) == 2

    def test_contains_risk_field(self, scripted_result):
        output = render_json(scripted_result)
        parsed = json.loads(output)
        for pkg in parsed["packages_with_scripts"]:
            assert "risk" in pkg
            assert pkg["risk"] in ("HIGH", "MEDIUM", "LOW")

    def test_affected_by_v12_list(self, scripted_result):
        output = render_json(scripted_result)
        parsed = json.loads(output)
        assert "esbuild" in parsed["packages_affected_by_v12"]
        assert "husky" in parsed["packages_affected_by_v12"]
