"""Tests for npm-shield core scanner and lockfile parser."""
import json
import os
import tempfile
from pathlib import Path

import pytest

from npm_shield.scanner import (
    find_install_scripts,
    classify_risk,
    scan_lockfile,
    ScanResult,
    PackageScriptInfo,
)
from npm_shield.errors import InvalidLockfileError, LockfileNotFoundError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SIMPLE_LOCKFILE = {
    "name": "my-project",
    "version": "1.0.0",
    "lockfileVersion": 3,
    "packages": {
        "": {
            "name": "my-project",
            "version": "1.0.0",
            "dependencies": {
                "express": "^4.18.0",
                "husky": "^8.0.0",
            },
        },
        "node_modules/express": {
            "version": "4.18.2",
            "resolved": "https://registry.npmjs.org/express/-/express-4.18.2.tgz",
        },
        "node_modules/husky": {
            "version": "8.3.7",
            "resolved": "https://registry.npmjs.org/husky/-/husky-8.3.7.tgz",
            "scripts": {
                "install": "node husky.js install",
                "prepublishOnly": "node husky.js",
            },
        },
    },
}

LOCKFILE_WITH_PREPOST = {
    "name": "complex-project",
    "version": "2.0.0",
    "lockfileVersion": 3,
    "packages": {
        "": {"name": "complex-project", "version": "2.0.0"},
        "node_modules/esbuild": {
            "version": "0.21.0",
            "resolved": "https://registry.npmjs.org/esbuild/-/esbuild-0.21.0.tgz",
            "scripts": {
                "postinstall": "node install.js",
                "preinstall": "node check-platform.js",
            },
        },
        "node_modules/cypress": {
            "version": "13.10.0",
            "resolved": "https://registry.npmjs.org/cypress/-/cypress-13.10.0.tgz",
            "scripts": {
                "install": "node index.js install",
            },
        },
        "node_modules/lodash": {
            "version": "4.17.21",
            "resolved": "https://registry.npmjs.org/lodash/-/lodash-4.17.21.tgz",
        },
        "node_modules/@types/node": {
            "version": "20.12.0",
            "resolved": "https://registry.npmjs.org/@types/node/-/node-20.12.0.tgz",
        },
    },
}

V2_LOCKFILE = {
    "name": "v2-project",
    "version": "1.0.0",
    "lockfileVersion": 2,
    "packages": {
        "": {"name": "v2-project", "version": "1.0.0"},
        "node_modules/fsevents": {
            "version": "1.2.13",
            "resolved": "https://registry.npmjs.org/fsevents/-/fsevents-1.2.13.tgz",
            "scripts": {"preinstall": "node install.js", "install": "node-gyp rebuild"},
            "os": ["darwin"],
        },
    },
}


@pytest.fixture
def tmp_lockfile(tmp_path):
    """Write a lockfile to a temp dir and return the path."""
    def _write(data, filename="package-lock.json"):
        path = tmp_path / filename
        path.write_text(json.dumps(data, indent=2))
        return path
    return _write


@pytest.fixture
def tmp_dir(tmp_path):
    """Return a tmp_path for use as cwd."""
    return tmp_path


# ---------------------------------------------------------------------------
# find_install_scripts
# ---------------------------------------------------------------------------

class TestFindInstallScripts:
    def test_finds_install_script(self):
        pkgs = SIMPLE_LOCKFILE["packages"]
        result = find_install_scripts(pkgs)
        assert "node_modules/husky" in result
        assert "install" in result["node_modules/husky"]
        assert "prepublishOnly" in result["node_modules/husky"]

    def test_returns_empty_when_no_scripts(self):
        pkgs = SIMPLE_LOCKFILE["packages"]
        pkgs = {"node_modules/express": pkgs["node_modules/express"]}
        result = find_install_scripts(pkgs)
        assert result == {}

    def test_finds_multiple_script_types(self):
        pkgs = LOCKFILE_WITH_PREPOST["packages"]
        result = find_install_scripts(pkgs)
        assert "node_modules/esbuild" in result
        scripts = result["node_modules/esbuild"]
        assert "postinstall" in scripts
        assert "preinstall" in scripts

    def test_empty_packages(self):
        result = find_install_scripts({})
        assert result == {}

    def test_ignores_root_entry(self):
        """Root package '' entry should be ignored."""
        pkgs = SIMPLE_LOCKFILE["packages"]
        result = find_install_scripts(pkgs)
        # Root has no scripts in this fixture, but even if it did, skip it
        assert "" not in result


# ---------------------------------------------------------------------------
# classify_risk
# ---------------------------------------------------------------------------

class TestClassifyRisk:
    def test_high_risk_multiple_scripts(self):
        info = PackageScriptInfo(
            name="esbuild",
            version="0.21.0",
            scripts={"postinstall": "node install.js", "preinstall": "node check.js"},
            resolved="https://registry.npmjs.org/esbuild/-/esbuild-0.21.0.tgz",
            is_dev=False,
        )
        assert classify_risk(info) == "HIGH"

    def test_medium_risk_single_install(self):
        info = PackageScriptInfo(
            name="husky",
            version="8.3.7",
            scripts={"install": "node husky.js install"},
            resolved="https://registry.npmjs.org/husky/-/husky-8.3.7.tgz",
            is_dev=True,
        )
        assert classify_risk(info) == "MEDIUM"

    def test_low_risk_only_prepublish(self):
        info = PackageScriptInfo(
            name="some-pkg",
            version="1.0.0",
            scripts={"prepublishOnly": "node build.js"},
            resolved="https://registry.npmjs.org/some-pkg/-/some-pkg-1.0.0.tgz",
            is_dev=False,
        )
        # prepublishOnly alone is not auto-run by npm v12 allowScripts
        assert classify_risk(info) == "LOW"


# ---------------------------------------------------------------------------
# scan_lockfile
# ---------------------------------------------------------------------------

class TestScanLockfile:
    def test_scan_v3_lockfile(self, tmp_lockfile, tmp_dir):
        path = tmp_lockfile(SIMPLE_LOCKFILE)
        result = scan_lockfile(str(path))
        assert isinstance(result, ScanResult)
        assert result.project_name == "my-project"
        assert result.lockfile_version == 3
        assert result.total_packages == 2  # 3 entries minus root ""
        assert len(result.packages_with_scripts) == 1

    def test_scan_v3_complex(self, tmp_lockfile, tmp_dir):
        path = tmp_lockfile(LOCKFILE_WITH_PREPOST)
        result = scan_lockfile(str(path))
        assert result.total_packages == 4  # 5 entries minus root ""
        assert len(result.packages_with_scripts) == 2  # esbuild + cypress

    def test_scan_v2_lockfile(self, tmp_lockfile, tmp_dir):
        path = tmp_lockfile(V2_LOCKFILE)
        result = scan_lockfile(str(path))
        assert result.lockfile_version == 2
        assert result.total_packages == 1
        assert len(result.packages_with_scripts) == 1  # fsevents

    def test_lockfile_not_found(self):
        with pytest.raises(LockfileNotFoundError):
            scan_lockfile("/nonexistent/package-lock.json")

    def test_invalid_lockfile(self, tmp_lockfile, tmp_dir):
        path = tmp_lockfile({"invalid": "data"}, "bad.json")
        # Missing both "packages" and "dependencies" keys
        with pytest.raises(InvalidLockfileError):
            scan_lockfile(str(path))


# ---------------------------------------------------------------------------
# ScanResult / PackageScriptInfo
# ---------------------------------------------------------------------------

class TestDataClasses:
    def test_package_script_info(self):
        info = PackageScriptInfo(
            name="test-pkg",
            version="1.2.3",
            scripts={"install": "node setup.js"},
            resolved="https://registry.npmjs.org/test-pkg/-/test-pkg-1.2.3.tgz",
            is_dev=False,
        )
        assert info.name == "test-pkg"
        assert info.is_install_script is True
        assert info.is_only_prepublish is False

    def test_prepublish_only(self):
        info = PackageScriptInfo(
            name="pub-pkg",
            version="1.0.0",
            scripts={"prepublishOnly": "echo hello"},
            resolved="https://registry.npmjs.org/pub-pkg/-/pub-pkg-1.0.0.tgz",
            is_dev=False,
        )
        assert info.is_install_script is False
        assert info.is_only_prepublish is True

    def test_scan_result_summary(self):
        info = PackageScriptInfo(
            name="x", version="1", scripts={"install": "a"},
            resolved="https://example.com", is_dev=False,
        )
        result = ScanResult(
            project_name="test",
            project_version="1.0.0",
            lockfile_version=3,
            total_packages=10,
            packages_with_scripts=[info],
            scan_path="/tmp/test",
        )
        assert result.summary() == (
            "Found 1 package(s) with install scripts out of 10 total."
        )
