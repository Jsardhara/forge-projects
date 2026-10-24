"""Tests for plugattest.cli — exit codes, JSON output, gates."""

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

from plugattest.cli import main


def _write(root, relpath, text):
    path = os.path.join(root, relpath)
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


def _run(argv):
    buf = io.StringIO()
    with redirect_stdout(buf), redirect_stderr(io.StringIO()):
        code = main(argv)
    return code, buf.getvalue()


class TestCli(unittest.TestCase):
    def test_clean_package_exits_zero_and_prints_pass(self):
        with tempfile.TemporaryDirectory() as root:
            _write(root, "package.json", json.dumps({"name": "d", "capabilities": []}))
            _write(root, "src/x.py", "print('hi')\n")
            code, out = _run([root])
        self.assertEqual(code, 0)
        self.assertIn("PASS", out)

    def test_undeclared_flags_exits_one(self):
        with tempfile.TemporaryDirectory() as root:
            _write(root, "package.json", json.dumps({"name": "d", "capabilities": ["network"]}))
            _write(root, "src/x.py", "import os\nos.system('id')\n")
            code, out = _run([root])
        self.assertEqual(code, 1)
        self.assertIn("PA-001", out)

    def test_fail_on_none_always_exits_zero(self):
        with tempfile.TemporaryDirectory() as root:
            _write(root, "package.json", json.dumps({"name": "d", "capabilities": []}))
            _write(root, "src/x.py", "import os\nos.system('id')\n")
            code, _ = _run([root, "--fail-on", "none"])
        self.assertEqual(code, 0)

    def test_fail_on_flag_passes_warn_level(self):
        with tempfile.TemporaryDirectory() as root:
            _write(root, "package.json", json.dumps({"name": "d", "version": "1"}))
            _write(root, "src/x.py", "import os\nos.system('id')\n")
            code, _ = _run([root, "--fail-on", "flag"])
        self.assertEqual(code, 0)

    def test_json_output_is_parseable(self):
        with tempfile.TemporaryDirectory() as root:
            _write(root, "package.json", json.dumps({"name": "d", "capabilities": ["network"]}))
            _write(root, "src/x.py", "import os\nos.system('id')\n")
            code, out = _run([root, "--json"])
        payload = json.loads(out)
        self.assertEqual(code, 1)
        self.assertEqual(payload["verdict"], "FLAG")
        self.assertTrue(any(f["code"] == "PA-001" for f in payload["findings"]))

    def test_missing_path_exits_usage_error(self):
        code, out = _run(["/nonexistent/plugattest/dir"])
        self.assertEqual(code, 2)
        self.assertIn("error", out.lower())

    def test_no_arguments_exits_usage_error(self):
        code, out = _run([])
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
