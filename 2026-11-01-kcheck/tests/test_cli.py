"""The exit-code contract, end to end, plus the two things a consumer depends on:
`--json` parses and carries provenance, and the human output names the tracker URL.
"""

import contextlib
import io
import json
import os
import subprocess
import sys
import time
import unittest

import helpers
from kcheck import cli

REPO_ROOT = helpers.PROJECT_ROOT


def run(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = cli.main(argv)
    return code, out.getvalue(), err.getvalue()


def fixture_dir(**kwargs):
    return helpers.fixtures(**kwargs)


class TestExitContract(unittest.TestCase):
    def test_fix_pending_host_exits_one(self):
        code, out, _ = run(["--fixtures", fixture_dir()])
        self.assertEqual(code, 1)
        self.assertIn("VULNERABLE", out)

    def test_human_output_names_kernel_target_gap_url_and_mitigation(self):
        _, out, _ = run(["--fixtures", fixture_dir()])
        self.assertIn("7.0.0-38-generic", out)      # the running kernel
        self.assertIn("7.0.0-38.38", out)           # the installed package version
        self.assertIn("7.0.0-43.43", out)           # the fixed target
        self.assertIn("5 ABI", out)                 # the gap
        self.assertIn("https://ubuntu.com/security/CVE-2026-98432", out)
        self.assertIn("mitigation", out.lower())

    def test_human_output_states_the_exposure_surface(self):
        _, out, _ = run(["--fixtures", fixture_dir()])
        self.assertIn("localhost", out)
        self.assertIn("tailnet", out)

    def test_patched_host_exits_zero(self):
        doc = helpers.table_doc(fix_state="released", fixed_version="7.0.0-38.38")
        code, out, _ = run(["--fixtures", fixture_dir(table=doc, sysctl="net.mptcp.enabled = 0\n",
                                                      ss=helpers.SS_EMPTY)])
        self.assertEqual(code, 0)
        self.assertIn("FIXED", out)

    def test_unknown_distro_exits_two(self):
        code, out, _ = run(["--fixtures", fixture_dir(os_release=helpers.OS_ARCH)])
        self.assertEqual(code, 2)
        self.assertIn("UNMEASURABLE", out)
        self.assertIn("arch", out)

    def test_unreadable_probes_exit_two(self):
        code, out, _ = run(["--fixtures", fixture_dir(uname=None, dpkg=None)])
        self.assertEqual(code, 2)

    def test_missing_fixture_dir_exits_two_and_does_not_crash(self):
        code, _, err = run(["--fixtures", "/nonexistent/kcheck-fixtures"])
        self.assertEqual(code, 2)
        self.assertIn("cannot", err.lower())

    def test_missing_table_exits_two_with_the_path_named(self):
        code, _, err = run(["--fixtures", fixture_dir(), "--table", "/nonexistent/table.json"])
        self.assertEqual(code, 2)
        self.assertIn("/nonexistent/table.json", err)

    def test_unknown_distro_never_infers_patched(self):
        # The whole point of exit 2: no row means "we cannot answer", never "you are fine".
        code, out, _ = run(["--fixtures", fixture_dir(os_release=helpers.OS_ARCH)])
        self.assertEqual(code, 2)
        self.assertNotIn("FIXED", out)
        self.assertNotIn("PASS", out)


class TestJson(unittest.TestCase):
    def setUp(self):
        self.code, self.out, _ = run(["--fixtures", fixture_dir(), "--json"])
        self.doc = json.loads(self.out)

    def test_json_parses_with_stdlib(self):
        self.assertIsInstance(self.doc, dict)

    def test_carries_exit_code_and_tool(self):
        self.assertEqual(self.doc["tool"], "kcheck")
        self.assertEqual(self.doc["exit_code"], 1)
        self.assertEqual(self.code, 1)

    def test_each_finding_carries_provenance(self):
        self.assertTrue(self.doc["findings"])
        for finding in self.doc["findings"]:
            with self.subTest(cve=finding["cve"]):
                self.assertTrue(finding["source_url"].startswith("https://"))
                self.assertRegex(finding["retrieved_at"], r"^\d{4}-\d\d-\d\dT")

    def test_two_axes_are_separate_booleans(self):
        finding = self.doc["findings"][0]
        self.assertIs(finding["in_range"], True)
        self.assertIs(finding["on_demonstrated_path"], True)

    def test_host_section_is_measured_not_asserted(self):
        host_doc = self.doc["host"]
        self.assertEqual(host_doc["running_release"], "7.0.0-38-generic")
        self.assertIs(host_doc["mptcp_enabled"], True)
        self.assertEqual(host_doc["mptcp_listener_count"], 5)
        self.assertEqual(host_doc["exposure_surface"], ["tailnet", "localhost"])

    def test_mitigation_is_a_pointer_not_an_action(self):
        m = self.doc["findings"][0]["mitigation"]
        self.assertFalse(m["automated"])
        self.assertTrue(m["pointer"])

    def test_json_only_on_stdout(self):
        self.assertEqual(self.out.strip()[0], "{")


class TestTableInjection(unittest.TestCase):
    def test_custom_table_changes_the_verdict(self):
        doc = helpers.table_doc(fix_state="released", fixed_version="7.0.0-43.43")
        code, _, _ = run(["--fixtures", fixture_dir(table=doc)])
        self.assertEqual(code, 1)  # 38.38 < 43.43 and no longer "pending"
        code, out, _ = run(["--fixtures", fixture_dir(table=doc), "--json"])
        self.assertEqual(json.loads(out)["findings"][0]["fix_state"], "released")

    def test_stale_row_is_visible(self):
        doc = helpers.table_doc(retrieved_at="2026-09-01T00:00:00Z")
        code, out, _ = run(["--fixtures", fixture_dir(table=doc), "--json"])
        finding = json.loads(out)["findings"][0]
        self.assertTrue(finding["provenance_stale"])
        self.assertGreater(finding["provenance_age_days"], 7)
        self.assertEqual(code, 1)


class TestPerformance(unittest.TestCase):
    def test_cold_run_under_two_seconds_on_fixtures(self):
        start = time.time()
        run(["--fixtures", fixture_dir(), "--quiet"])
        self.assertLess(time.time() - start, 2.0)


class TestLauncher(unittest.TestCase):
    """`./kcheck` must work with no install step and no PYTHONPATH."""

    def test_launcher_exists_and_is_executable(self):
        path = os.path.join(REPO_ROOT, "kcheck")
        self.assertTrue(os.path.isfile(path))
        self.assertTrue(os.access(path, os.X_OK))

    def test_launcher_runs_on_fixtures_with_json(self):
        path = os.path.join(REPO_ROOT, "kcheck")
        proc = subprocess.run([sys.executable, path, "--fixtures", fixture_dir(), "--json"],
                              capture_output=True, text=True, timeout=30)
        self.assertEqual(proc.returncode, 1, proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["tool"], "kcheck")

    def test_launcher_unknown_distro_exits_two(self):
        path = os.path.join(REPO_ROOT, "kcheck")
        proc = subprocess.run([sys.executable, path, "--fixtures",
                               fixture_dir(os_release=helpers.OS_ARCH)],
                              capture_output=True, text=True, timeout=30)
        self.assertEqual(proc.returncode, 2)


class TestLiveHost(unittest.TestCase):
    """On this host the answer is known and measured. Skip elsewhere (CI, other boxes)."""

    @classmethod
    def setUpClass(cls):
        cls.release = cli_host_release()

    def test_live_run_matches_the_recorded_measurement(self):
        if not self.release.startswith("7.0.0-38"):
            self.skipTest("host kernel is %r, not the 2026-11-01 measurement" % self.release)
        code, out, _ = run([])
        self.assertEqual(code, 1, out)
        self.assertIn("7.0.0-38-generic", out)
        self.assertIn("7.0.0-43.43", out)
        self.assertIn("fix_pending", out)


def cli_host_release():
    try:
        return subprocess.run(["uname", "-r"], capture_output=True, text=True,
                              timeout=5).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


if __name__ == "__main__":
    unittest.main()
