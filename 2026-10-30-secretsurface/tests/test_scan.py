"""End-to-end scan tests: classification, dedupe, exit-code contract."""
import tempfile
import unittest
from pathlib import Path

from secretsurface.scan import scan, Report


def akia():
    return "AKIA" + "Q7FZ2M4XB9PLR3TK"


def gh_token():
    return "ghp_" + "a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8"


class ScanTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, rel, content):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def test_clean_tree_produces_no_findings(self):
        self.write("notes.txt", "nothing to see here\n")
        report = scan([self.root])
        self.assertEqual(report.findings, [])
        self.assertTrue(report.is_clean())

    def test_hit_in_a_dot_directory_is_found_and_classified(self):
        self.write(".curator_backups/blobs/ab12cd", "v=" + akia() + "\n")
        report = scan([self.root])
        self.assertEqual(len(report.findings), 1)
        self.assertEqual(report.findings[0].klass, "backup-blob")

    def test_env_backup_is_classified_as_env_backup(self):
        self.write("p/.env.bak.si09-20260911", "KEY=" + akia() + "\n")
        report = scan([self.root])
        self.assertEqual(report.findings[0].klass, "env-backup")

    def test_activity_log_is_classified_as_log_leak(self):
        self.write("p/foreman_activity.jsonl", '{"k":"' + gh_token() + '"}\n')
        report = scan([self.root])
        self.assertEqual(report.findings[0].klass, "log-leak")

    def test_multiple_patterns_in_one_file_all_reported(self):
        self.write("p/.env", "A=" + akia() + "\nB=" + gh_token() + "\n")
        report = scan([self.root])
        ids = sorted(f.pattern_id for f in report.findings)
        self.assertEqual(ids, ["aws-access-key", "github-token"])

    def test_same_secret_in_two_files_is_two_findings_one_fingerprint(self):
        self.write("a/.env", "K=" + akia() + "\n")
        self.write("b/.env.bak.1", "K=" + akia() + "\n")
        report = scan([self.root])
        self.assertEqual(len(report.findings), 2)
        self.assertEqual(len({f.fingerprint for f in report.findings}), 1)

    def test_findings_carry_blast_signals(self):
        self.write("a/.env.bak.1", "K=" + akia() + "\n")
        report = scan([self.root])
        self.assertIn("superseded-key-may-still-validate",
                      report.findings[0].signals)

    def test_counts_are_reported(self):
        self.write("a.txt", "x\n")
        self.write("b.txt", "y\n")
        report = scan([self.root])
        self.assertEqual(report.files_scanned, 2)

    def test_scan_is_deterministic(self):
        self.write("b/.env", "K=" + akia() + "\n")
        self.write("a/.env", "K=" + gh_token() + "\n")
        one = [(f.path, f.line, f.pattern_id) for f in scan([self.root]).findings]
        two = [(f.path, f.line, f.pattern_id) for f in scan([self.root]).findings]
        self.assertEqual(one, two)

    def test_report_exposes_worst_class_for_verdict(self):
        self.write("a/.env", "K=" + akia() + "\n")
        report = scan([self.root])
        self.assertEqual(report.counts_by_class(), {"env": 1})

    def test_missing_root_makes_the_report_unmeasurable(self):
        report = scan([self.root / "nope"])
        self.assertTrue(report.is_unmeasurable())

    def test_unmeasurable_report_is_not_clean(self):
        report = scan([self.root / "nope"])
        self.assertFalse(report.is_clean())

    def test_empty_tree_is_unmeasurable_not_clean(self):
        # zero files read means we proved nothing, so it cannot be called clean
        report = scan([self.root])
        self.assertTrue(report.is_unmeasurable())


class ExitCodeTests(unittest.TestCase):
    def test_clean_exit_is_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "a.txt").write_text("hi\n")
            self.assertEqual(scan([Path(tmp)]).exit_code(), 0)

    def test_findings_exit_is_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, ".env").write_text("K=" + akia() + "\n")
            self.assertEqual(scan([Path(tmp)]).exit_code(), 1)

    def test_unmeasurable_exit_is_two(self):
        self.assertEqual(scan([Path("/definitely/not/here")]).exit_code(), 2)


if __name__ == "__main__":
    unittest.main()
