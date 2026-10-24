"""Tests for plugattest.attest — declared-vs-detected diff and verdict."""

import json
import os
import tempfile
import unittest

from plugattest.attest import attest, EXIT_CLEAN, EXIT_FINDINGS, EXIT_USAGE


def _write(root, relpath, text):
    path = os.path.join(root, relpath)
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


def _codes(report):
    return {f.code for f in report.findings}


class TestUndeclared(unittest.TestCase):
    def test_undeclared_capability_flags(self):
        with tempfile.TemporaryDirectory() as root:
            _write(root, "package.json", json.dumps({"name": "d", "capabilities": ["network"]}))
            _write(root, "src/x.py", "import os\nos.system('id')\n")
            report = attest(root)
        self.assertIn("PA-001", _codes(report))
        self.assertEqual(report.verdict.name, "FLAG")
        self.assertIn("shell", [f.capability for f in report.findings if f.code == "PA-001"])

    def test_declared_capability_is_clean(self):
        with tempfile.TemporaryDirectory() as root:
            _write(root, "package.json", json.dumps({"name": "d", "capabilities": ["network"]}))
            _write(root, "src/x.py", "import urllib.request\nurllib.request.urlopen('https://a')\n")
            report = attest(root)
        self.assertNotIn("PA-001", _codes(report))
        self.assertEqual(report.verdict.name, "PASS")

    def test_declared_but_unused_is_info_only(self):
        with tempfile.TemporaryDirectory() as root:
            _write(root, "package.json",
                   json.dumps({"name": "d", "capabilities": ["network", "shell"]}))
            _write(root, "src/x.py", "import urllib.request\nurllib.request.urlopen('https://a')\n")
            report = attest(root)
        self.assertIn("PA-002", _codes(report))
        self.assertEqual(report.verdict.name, "INFO")


class TestMissingDeclaration(unittest.TestCase):
    def test_none_detected_none_declared_is_clean(self):
        with tempfile.TemporaryDirectory() as root:
            _write(root, "src/x.py", "print('hello')\n")
            report = attest(root)
        self.assertEqual(report.verdict.name, "PASS")

    def test_no_manifest_but_capabilities_used_fails_closed(self):
        with tempfile.TemporaryDirectory() as root:
            _write(root, "src/x.py", "import os\nos.system('id')\n")
            report = attest(root)
        self.assertIn("PA-005", _codes(report))
        self.assertEqual(report.verdict.name, "FLAG")

    def test_manifest_without_capability_key_warns(self):
        with tempfile.TemporaryDirectory() as root:
            _write(root, "package.json", json.dumps({"name": "d", "version": "1"}))
            _write(root, "src/x.py", "import os\nos.system('id')\n")
            report = attest(root)
        self.assertIn("PA-003", _codes(report))
        self.assertEqual(report.verdict.name, "WARN")

    def test_unknown_declared_capability_warns(self):
        with tempfile.TemporaryDirectory() as root:
            _write(root, "package.json", json.dumps({"name": "d", "capabilities": ["telepathy"]}))
            _write(root, "src/x.py", "print('x')\n")
            report = attest(root)
        self.assertIn("PA-006", _codes(report))
        self.assertEqual(report.verdict.name, "WARN")


class TestHooks(unittest.TestCase):
    def test_undeclared_postinstall_flags(self):
        with tempfile.TemporaryDirectory() as root:
            _write(root, "package.json", json.dumps({
                "name": "d", "capabilities": ["network"],
                "scripts": {"postinstall": "node setup.js"},
            }))
            _write(root, "src/x.py", "import urllib.request\nurllib.request.urlopen('https://a')\n")
            report = attest(root)
        self.assertIn("PA-004", _codes(report))
        self.assertEqual(report.verdict.name, "FLAG")

    def test_declared_hook_is_clean(self):
        with tempfile.TemporaryDirectory() as root:
            _write(root, "package.json", json.dumps({
                "name": "d", "capabilities": ["network", "auto_hook"],
                "scripts": {"postinstall": "node setup.js"},
            }))
            _write(root, "src/x.py", "import urllib.request\nurllib.request.urlopen('https://a')\n")
            report = attest(root)
        self.assertNotIn("PA-004", _codes(report))


class TestExitCodes(unittest.TestCase):
    def _exit_for(self, root):
        report = attest(root)
        if report.verdict.name in ("PASS", "INFO"):
            return EXIT_CLEAN
        return EXIT_FINDINGS

    def test_clean_package_exits_zero(self):
        with tempfile.TemporaryDirectory() as root:
            _write(root, "package.json", json.dumps({"name": "d", "capabilities": []}))
            _write(root, "src/x.py", "print('hi')\n")
            self.assertEqual(self._exit_for(root), EXIT_CLEAN)

    def test_missing_directory_raises(self):
        with self.assertRaises(OSError):
            attest("/nonexistent/plugattest/dir")

    def test_exit_codes_are_distinct(self):
        self.assertEqual(len({EXIT_CLEAN, EXIT_FINDINGS, EXIT_USAGE}), 3)


if __name__ == "__main__":
    unittest.main()
