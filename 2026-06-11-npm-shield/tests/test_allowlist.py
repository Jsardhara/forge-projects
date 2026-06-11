"""Tests for npm-shield allowlist generator."""
import json

import pytest

from npm_shield.scanner import PackageScriptInfo, ScanResult
from npm_shield.allowlist import generate_allowlist, generate_allowlist_json


@pytest.fixture
def scan_result_with_scripts():
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
    only_publish = [
        PackageScriptInfo(
            name="safe-pkg", version="1.0.0",
            scripts={"prepublishOnly": "echo hello"},
            resolved="https://registry.npmjs.org/safe-pkg/-/safe-pkg-1.0.0.tgz",
        ),
    ]
    return ScanResult(
        project_name="test-proj",
        project_version="1.0.0",
        lockfile_version=3,
        total_packages=10,
        packages_with_scripts=affected + only_publish,
        scan_path="/tmp/test",
    )


class TestGenerateAllowlist:
    def test_contains_authorization_key(self, scan_result_with_scripts):
        result = generate_allowlist(scan_result_with_scripts)
        assert "authorization" in result
        assert "authorizedPackages" in result["authorization"]

    def test_excludes_publish_only_packages(self, scan_result_with_scripts):
        result = generate_allowlist(scan_result_with_scripts)
        pkgs = result["authorization"]["authorizedPackages"]
        # safe-prepublish-only package should NOT be in allowlist
        key = "safe-pkg@1.0.0"
        assert key not in pkgs

    def test_includes_install_script_packages(self, scan_result_with_scripts):
        result = generate_allowlist(scan_result_with_scripts)
        pkgs = result["authorization"]["authorizedPackages"]
        assert "esbuild@0.21.0" in pkgs
        assert "husky@8.3.7" in pkgs

    def test_script_names_included(self, scan_result_with_scripts):
        result = generate_allowlist(scan_result_with_scripts)
        pkgs = result["authorization"]["authorizedPackages"]
        esbuild_scripts = pkgs["esbuild@0.21.0"]
        assert "postinstall" in esbuild_scripts
        assert "preinstall" in esbuild_scripts

    def test_empty_when_no_affected_packages(self):
        result_empty = ScanResult(
            project_name="clean",
            project_version="1.0.0",
            lockfile_version=3,
            total_packages=5,
            packages_with_scripts=[],
            scan_path="/tmp/clean",
        )
        result = generate_allowlist(result_empty)
        assert result["authorization"]["authorizedPackages"] == {}

    def test_json_output_is_valid_json(self, scan_result_with_scripts):
        json_str = generate_allowlist_json(scan_result_with_scripts)
        parsed = json.loads(json_str)
        assert "authorization" in parsed
