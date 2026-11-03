"""CLI: the single exit contract, --diff, --json, and never-crash behaviour."""

import contextlib
import io
import json
import os
import tempfile
import unittest

from posture.cli import main

# Reads its exit code from a file so a test can flip it between runs.
FILE_EXIT_CLI = '''
import os, sys
code = open(os.path.join(os.path.dirname(__file__), "../../code.txt")).read().strip()
sys.stdout.write("VERDICT=%s\\n" % code)
sys.exit(int(code))
'''

# The repo convention: every verifier package ships a __main__.py that runs cli.
MAIN = (
    "import os, runpy\n"
    "runpy.run_path(os.path.join(os.path.dirname(__file__), 'cli.py'), run_name='__main__')\n"
)


class CliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        self.state = os.path.join(self.root, "state", "posture.json")

    def tearDown(self):
        self.tmp.cleanup()

    def add(self, name, source=FILE_EXIT_CLI, code="0"):
        d = os.path.join(self.root, "2026-01-01-" + name)
        pkg = os.path.join(d, "src", name)
        os.makedirs(pkg, exist_ok=True)
        open(os.path.join(pkg, "__init__.py"), "w").close()
        with open(os.path.join(pkg, "cli.py"), "w") as fh:
            fh.write(source)
        with open(os.path.join(pkg, "__main__.py"), "w") as fh:
            fh.write(MAIN)
        with open(os.path.join(d, "code.txt"), "w") as fh:
            fh.write(code + "\n")
        return d

    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = main(list(argv))
        return rc, out.getvalue(), err.getvalue()

    def base_args(self):
        return ["--repo-root", self.root, "--state", self.state, "--all"]

    def test_default_run_ignores_unregistered_projects(self):
        self.add("alpha", code="1")
        rc, _, err = self.run_cli("--repo-root", self.root, "--state", self.state)
        self.assertEqual(rc, 2)
        self.assertIn("no verifiers", err.lower())

    def test_never_runs_itself(self):
        self.add("posture", code="0")
        self.add("alpha", code="0")
        rc, out, _ = self.run_cli(*self.base_args())
        self.assertEqual(rc, 0)
        self.assertNotIn("posture (", out)

    # --- exit contract -------------------------------------------------
    def test_all_clean_exits_0(self):
        self.add("alpha")
        rc, out, _ = self.run_cli(*self.base_args())
        self.assertEqual(rc, 0)
        self.assertIn("all clear", out.lower())

    def test_findings_exits_1(self):
        self.add("alpha", code="1")
        rc, out, _ = self.run_cli(*self.base_args())
        self.assertEqual(rc, 1)

    def test_unmeasurable_exits_2_even_with_findings(self):
        self.add("alpha", code="1")
        self.add("beta", code="2")
        rc, _, _ = self.run_cli(*self.base_args())
        self.assertEqual(rc, 2)

    def test_timeout_makes_run_partial(self):
        self.add("alpha", source="import time\ntime.sleep(5)\n")
        rc, out, _ = self.run_cli(*self.base_args(), "--timeout", "1")
        self.assertEqual(rc, 2)
        self.assertIn("alpha", out)

    def test_missing_root_exits_2_and_says_why(self):
        rc, _, err = self.run_cli(
            "--repo-root", os.path.join(self.root, "nope"), "--state", self.state
        )
        self.assertEqual(rc, 2)
        self.assertIn("repo-root", err)

    def test_no_verifiers_found_exits_2(self):
        rc, _, err = self.run_cli(*self.base_args())
        self.assertEqual(rc, 2)
        self.assertIn("no verifiers", err.lower())

    # --- transition reporting ------------------------------------------
    def test_first_run_reports_baseline_not_transitions(self):
        self.add("alpha")
        rc, out, _ = self.run_cli(*self.base_args(), "--diff")
        self.assertEqual(rc, 0)
        self.assertIn("baseline", out.lower())
        self.assertNotIn("TRANSITION", out)

    def test_second_identical_run_is_silent_about_transitions(self):
        self.add("alpha")
        self.run_cli(*self.base_args(), "--diff")
        rc, out, _ = self.run_cli(*self.base_args(), "--diff")
        self.assertIn("no transitions", out.lower())
        self.assertNotIn("TRANSITION", out)

    def test_changed_verdict_is_reported_as_transition(self):
        d = self.add("alpha", source=FILE_EXIT_CLI, code="0")
        self.run_cli(*self.base_args(), "--diff")
        with open(os.path.join(d, "code.txt"), "w") as fh:
            fh.write("1\n")
        rc, out, _ = self.run_cli(*self.base_args(), "--diff")
        self.assertEqual(rc, 1)
        self.assertIn("TRANSITION", out)
        self.assertIn("clean -> findings", out)

    def test_state_persists_per_verifier_rows(self):
        self.add("alpha")
        self.run_cli(*self.base_args())
        with open(self.state) as fh:
            saved = json.load(fh)
        self.assertEqual(list(saved["rows"]), ["alpha"])

    def test_no_save_does_not_write(self):
        self.add("alpha")
        self.run_cli(*self.base_args(), "--no-save")
        self.assertFalse(os.path.exists(self.state))

    # --- machine output -------------------------------------------------
    def test_json_is_parseable_and_carries_contract(self):
        self.add("alpha", code="1")
        rc, out, _ = self.run_cli(*self.base_args(), "--json")
        self.assertEqual(rc, 1)
        payload = json.loads(out)
        self.assertEqual(payload["exit"], 1)
        self.assertEqual(payload["results"][0]["name"], "alpha")
        self.assertEqual(payload["results"][0]["status"], "findings")
        self.assertIn("transitions", payload)
        self.assertNotIn("stdout", payload["results"][0])

    def test_quiet_prints_nothing_when_clean(self):
        self.add("alpha")
        rc, out, _ = self.run_cli(*self.base_args(), "--quiet")
        self.assertEqual(rc, 0)
        self.assertEqual(out.strip(), "")

    def test_quiet_still_prints_on_findings(self):
        self.add("alpha", code="1")
        rc, out, _ = self.run_cli(*self.base_args(), "--quiet")
        self.assertEqual(rc, 1)
        self.assertTrue(out.strip())

    # --- selection -------------------------------------------------------
    def test_only_limits_the_set(self):
        self.add("alpha")
        self.add("beta", code="1")
        rc, out, _ = self.run_cli(*self.base_args(), "--only", "alpha")
        self.assertEqual(rc, 0)
        self.assertNotIn("beta", out)

    def test_only_unknown_exits_2(self):
        self.add("alpha")
        rc, _, err = self.run_cli(*self.base_args(), "--only", "nope")
        self.assertEqual(rc, 2)
        self.assertIn("nope", err)


if __name__ == "__main__":
    unittest.main()
