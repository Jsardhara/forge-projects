"""CLI exit-code contract end to end."""

import contextlib
import io
import json
import unittest

import helpers
from tsattest import cli


def run_cli(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = cli.main(argv)
    return code, out.getvalue(), err.getvalue()


def fixtures(version="1.102.3", prefs=helpers.PREFS_SSH_ON, serve=None, environ=None,
             defaults=None):
    return helpers.write_fixtures(helpers.tempdir(), version=version, prefs=prefs,
                                  status=helpers.status_doc(ssh_host_keys=None),
                                  serve=serve, environ=environ, defaults=defaults)


class TestExitCodes(unittest.TestCase):
    def test_vulnerable_exits_one(self):
        code, out, _ = run_cli(["--fixtures", fixtures()])
        self.assertEqual(code, 1)
        self.assertIn("FAIL", out)

    def test_patched_exits_zero(self):
        code, out, _ = run_cli(["--fixtures", fixtures(version="1.104.4", serve="")])
        self.assertEqual(code, 0)
        self.assertIn("PASS", out)

    def test_unmeasurable_exits_two(self):
        code, out, _ = run_cli(["--fixtures", fixtures(version=None)])
        self.assertEqual(code, 2)
        self.assertIn("UNKNOWN", out)

    def test_json_flag_emits_only_json(self):
        code, out, _ = run_cli(["--fixtures", fixtures(), "--json"])
        self.assertEqual(code, 1)
        doc = json.loads(out)
        self.assertEqual(doc["verdict"], "FAIL")

    def test_missing_fixture_dir_is_unmeasurable_not_a_crash(self):
        code, out, _ = run_cli(["--fixtures", "/nonexistent/tsattest-fixtures"])
        self.assertEqual(code, 2)
        self.assertIn("UNKNOWN", out)


class TestRealProbeMode(unittest.TestCase):
    def test_live_mode_without_tailscale_binary_is_unmeasurable(self):
        # A nonexistent binary must produce UNKNOWN with the command named,
        # never a traceback and never an optimistic PASS.
        code, out, _ = run_cli(["--tailscale-bin", "/nonexistent/tailscale"])
        self.assertEqual(code, 2)
        self.assertIn("UNKNOWN", out)
        self.assertIn("/nonexistent/tailscale", out)


if __name__ == "__main__":
    unittest.main()
