"""End-to-end CLI: real fixture page, injected host facts, temp state file. No network."""

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout

from cvewatch.cli import main

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "ubuntu_cve_excerpt.html")
HOST_ARGS = ["--no-host", "--release", "26.04", "--codename", "resolute"]


class CliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state = os.path.join(self.tmp.name, "state.json")

    def tearDown(self):
        self.tmp.cleanup()

    def run_cli(self, *args):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = main(list(args))
        return code, buffer.getvalue()

    def base(self, installed):
        return ["--page", FIXTURE, "--state", self.state, "--cve", "CVE-2026-98432"] + \
            HOST_ARGS + ["--installed", installed]

    def test_vulnerable_pending_fix_exits_1(self):
        code, output = self.run_cli(*self.base("linux-image-7.0.0-38-generic=7.0.0-38.38"))
        self.assertEqual(code, 1)
        self.assertIn("VULNERABLE_PENDING_FIX", output)
        self.assertIn("7.0.0-43.43", output)
        self.assertIn("not released", output)

    def test_patched_exits_0(self):
        code, output = self.run_cli(*self.base("linux-image-7.0.0-43-generic=7.0.0-43.43"))
        self.assertEqual(code, 0)
        self.assertIn("PATCHED", output)

    def test_release_missing_exits_2(self):
        args = self.base("linux-image-7.0.0-38-generic=7.0.0-38.38")
        # 25.04 does not appear in the excerpt at all -> unmeasurable, never "clean".
        args[args.index("26.04")] = "25.04"
        args[args.index("resolute")] = "plucky"
        code, output = self.run_cli(*args)
        self.assertEqual(code, 2)
        self.assertIn("UNKNOWN", output)

    def test_installed_override_with_source(self):
        code, _ = self.run_cli(*self.base(
            "linux-hwe:linux-image-6.8.0-40-generic=6.8.0-40.40"))
        self.assertEqual(code, 0)
        # linux-hwe 26.04 row is "Not in release"

    def test_json_output_is_parseable(self):
        code, output = self.run_cli("--json", *self.base(
            "linux-image-7.0.0-38-generic=7.0.0-38.38"))
        document = json.loads(output)
        self.assertEqual(code, 1)
        self.assertEqual(document["exit_code"], 1)
        self.assertEqual(document["results"][0]["cve"], "CVE-2026-98432")
        self.assertEqual(document["results"][0]["verdict"], "VULNERABLE_PENDING_FIX")
        self.assertEqual(document["results"][0]["rows"][0]["binary"],
                         "linux-image-7.0.0-38-generic")

    def test_quiet_prints_nothing(self):
        code, output = self.run_cli("--quiet", *self.base(
            "linux-image-7.0.0-38-generic=7.0.0-38.38"))
        self.assertEqual(output, "")
        self.assertEqual(code, 1)

    def test_state_written_and_reused_for_diff(self):
        first_code, _ = self.run_cli("--diff", *self.base(
            "linux-image-7.0.0-38-generic=7.0.0-38.38"))
        self.assertTrue(os.path.exists(self.state))
        self.assertEqual(first_code, 1)
        second_code, output = self.run_cli("--diff", *self.base(
            "linux-image-7.0.0-43-generic=7.0.0-43.43"))
        self.assertEqual(second_code, 0)
        self.assertIn("TRANSITIONS", output)
        self.assertIn("verdict_changed", output)
        self.assertIn("VULNERABLE_PENDING_FIX", output)

    def test_second_identical_run_has_no_transitions(self):
        args = self.base("linux-image-7.0.0-38-generic=7.0.0-38.38")
        self.run_cli("--diff", *args)
        code, output = self.run_cli("--diff", *args)
        self.assertEqual(code, 1)
        self.assertNotIn("TRANSITIONS", output)

    def test_no_save_leaves_state_absent(self):
        self.run_cli("--no-save", *self.base("linux-image-7.0.0-38-generic=7.0.0-38.38"))
        self.assertFalse(os.path.exists(self.state))

    def test_no_cve_is_an_error_exit_2(self):
        code, _ = self.run_cli("--no-host", "--release", "26.04")
        self.assertEqual(code, 2)

    def test_bad_cve_id_is_an_error_exit_2(self):
        code, _ = self.run_cli("--cve", "not-a-cve", "--no-host", "--release", "26.04")
        self.assertEqual(code, 2)

    def test_page_mismatch_is_unknown_not_clean(self):
        args = ["--page", FIXTURE, "--state", self.state, "--cve", "CVE-2099-0001"] + \
            HOST_ARGS + ["--installed", "linux-image-7.0.0-38-generic=7.0.0-38.38"]
        code, output = self.run_cli(*args)
        self.assertEqual(code, 2)
        self.assertIn("page is for", output)

    def test_multiple_cves_with_one_page_is_rejected(self):
        code, _ = self.run_cli("--page", FIXTURE, "--cve", "CVE-2026-98432",
                               "--cve", "CVE-2026-11111", "--no-host", "--release", "26.04")
        self.assertEqual(code, 2)

    def test_fetch_failure_is_unknown_exit_2(self):
        # A page that cannot be read must be UNKNOWN, never "clean". A local missing file
        # proves the failure path without depending on network conditions.
        args = ["--page", os.path.join(self.tmp.name, "absent.html"), "--state", self.state,
                "--cve", "CVE-2026-98432"] + HOST_ARGS + \
            ["--installed", "linux-image-7.0.0-38-generic=7.0.0-38.38"]
        code, output = self.run_cli(*args)
        self.assertEqual(code, 2)
        self.assertIn("UNKNOWN", output)


class CveFileTests(unittest.TestCase):
    def test_cve_file_with_comments(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "cves.txt")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("# watch list\nCVE-2026-98432\n\n")
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                code = main(["--page", FIXTURE, "--cve-file", path, "--state",
                             os.path.join(tmp, "s.json"), "--no-host", "--release", "26.04",
                             "--codename", "resolute", "--installed",
                             "linux-image-7.0.0-38-generic=7.0.0-38.38"])
        self.assertEqual(code, 1)
        self.assertIn("CVE-2026-98432", buffer.getvalue())


if __name__ == "__main__":
    unittest.main()
