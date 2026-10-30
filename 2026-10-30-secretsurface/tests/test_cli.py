"""CLI contract: 0 clean, 1 findings, 2 unmeasurable. Never echoes a secret."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from secretsurface.cli import main


def akia():
    return "AKIA" + "Q7FZ2M4XB9PLR3TK"


class CliTests(unittest.TestCase):
    def run_cli(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(argv)
        return code, out.getvalue(), err.getvalue()

    def clean_root(self, tmp):
        Path(tmp, "notes.txt").write_text("nothing\n")
        return tmp

    def dirty_root(self, tmp):
        Path(tmp, ".env.bak.old").write_text("K=" + akia() + "\n")
        return tmp

    def test_clean_root_exits_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, out, _ = self.run_cli([self.clean_root(tmp)])
            self.assertEqual(code, 0)
            self.assertIn("clean", out.lower())

    def test_findings_exit_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, out, _ = self.run_cli([self.dirty_root(tmp)])
            self.assertEqual(code, 1)
            self.assertIn("env-backup", out)

    def test_missing_root_exits_two(self):
        code, out, _ = self.run_cli(["/definitely/not/here"])
        self.assertEqual(code, 2)
        self.assertIn("unmeasurable", out.lower())

    def test_secret_is_never_printed(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, out, err = self.run_cli([self.dirty_root(tmp)])
            self.assertNotIn(akia(), out + err)
            self.assertNotIn(akia()[4:20], out + err)

    def test_json_mode_is_valid_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, out, _ = self.run_cli(["--json", self.dirty_root(tmp)])
            self.assertEqual(code, 1)
            data = json.loads(out)
            self.assertEqual(data["summary"]["findings"], 1)
            self.assertEqual(data["findings"][0]["klass"], "env-backup")

    def test_revoke_list_mode_prints_only_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.dirty_root(tmp)
            code, out, _ = self.run_cli(["--revoke-list", root])
            self.assertEqual(code, 1)
            lines = [line for line in out.splitlines() if line.strip()]
            self.assertEqual(len(lines), 1)
            self.assertTrue(lines[0].startswith(root))
            self.assertNotIn("env-backup", lines[0])

    def test_quiet_mode_prints_nothing_on_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, out, _ = self.run_cli(["--quiet", self.clean_root(tmp)])
            self.assertEqual(code, 0)
            self.assertEqual(out, "")

    def test_multiple_roots_are_all_scanned(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            Path(a, ".env").write_text("K=" + akia() + "\n")
            self.clean_root(b)
            code, out, _ = self.run_cli(["--json", a, b])
            self.assertEqual(code, 1)
            self.assertEqual(json.loads(out)["summary"]["findings"], 1)

    def test_bare_invocation_scans_default_roots(self):
        # A bare run is the fleet-report shape: no args, documented surfaces.
        # It must not be a usage error, and it must say which roots it used.
        code, out, err = self.run_cli([])
        self.assertIn(code, (0, 1, 2))
        self.assertNotIn("usage", err.lower())
        self.assertIn("roots:", out.lower())

    def test_default_roots_include_profiles_and_skills(self):
        from secretsurface.cli import default_roots
        rendered = " ".join(str(p) for p in default_roots(Path("/h")))
        self.assertIn("profiles", rendered)
        self.assertIn("skills", rendered)

    def test_scan_report_states_what_was_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.clean_root(tmp)
            Path(tmp, "blob.bin").write_bytes(b"\x00\x01")
            _, out, _ = self.run_cli([tmp])
            self.assertIn("skipped", out.lower())


if __name__ == "__main__":
    unittest.main()
