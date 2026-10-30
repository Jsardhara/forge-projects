"""Tests for blast-radius signals and the report renderers."""
import os
import tempfile
import unittest
from pathlib import Path

from secretsurface.blast import blast_signals, summarise_by_root
from secretsurface.scan import Finding, Report


def akia():
    return "AKIA" + "Q7FZ2M4XB9PLR3TK"


class BlastSignalTests(unittest.TestCase):
    def test_world_readable_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "f.txt"
            path.write_text("x")
            os.chmod(path, 0o644)
            self.assertIn("world-readable", blast_signals(path, "unknown"))

    def test_owner_only_file_is_not_flagged_world_readable(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "f.txt"
            path.write_text("x")
            os.chmod(path, 0o600)
            self.assertNotIn("world-readable", blast_signals(path, "unknown"))

    def test_file_inside_git_worktree_is_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / ".git").mkdir()
            path = Path(tmp) / "f.txt"
            path.write_text("x")
            self.assertIn("in-git-worktree", blast_signals(path, "unknown"))

    def test_file_outside_git_is_not_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "f.txt"
            path.write_text("x")
            self.assertNotIn("in-git-worktree", blast_signals(path, "unknown"))

    def test_env_backup_class_implies_superseded_but_live(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "f.txt"
            path.write_text("x")
            self.assertIn("superseded-key-may-still-validate",
                          blast_signals(path, "env-backup"))

    def test_log_class_implies_copied_channel(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "f.jsonl"
            path.write_text("x")
            self.assertIn("copied-or-shipped", blast_signals(path, "log-leak"))

    def test_missing_file_does_not_raise(self):
        self.assertEqual(blast_signals(Path("/nope/nope"), "unknown"), ())


class SummaryTests(unittest.TestCase):
    def finding(self, path, klass):
        return Finding(path=path, line=1, pattern_id="aws-access-key",
                       fingerprint="abcd", value_len=20, klass=klass,
                       signals=())

    def test_summarise_counts_by_root_and_class(self):
        findings = [
            self.finding("/roots/a/x/.env", "env"),
            self.finding("/roots/a/x/.env.bak.1", "env-backup"),
            self.finding("/roots/b/y/log.jsonl", "log-leak"),
        ]
        summary = summarise_by_root(findings, roots=[Path("/roots/a"), Path("/roots/b")])
        self.assertEqual(summary["/roots/a"]["total"], 2)
        self.assertEqual(summary["/roots/a"]["classes"]["env"], 1)
        self.assertEqual(summary["/roots/b"]["classes"]["log-leak"], 1)

    def test_summarise_reports_zeros_for_a_root_with_no_hits(self):
        summary = summarise_by_root([], roots=[Path("/roots/clean")])
        self.assertEqual(summary["/roots/clean"]["total"], 0)


class ReportRenderTests(unittest.TestCase):
    def report(self):
        f = Finding(path="/r/p/.env.bak.1", line=7, pattern_id="aws-access-key",
                    fingerprint="9f2c", value_len=20, klass="env-backup",
                    signals=("in-git-worktree",))
        return Report(roots=["/r"], findings=[f], skipped=[],
                      files_scanned=3, files_skipped=0)

    def test_text_report_names_path_line_and_class(self):
        out = self.report().as_text()
        self.assertIn("/r/p/.env.bak.1", out)
        self.assertIn(":7", out)
        self.assertIn("env-backup", out)
        self.assertIn("aws-access-key", out)

    def test_text_report_prints_the_fingerprint(self):
        self.assertIn("9f2c", self.report().as_text())

    def test_text_report_never_prints_a_secret(self):
        self.assertNotIn(akia(), self.report().as_text())

    def test_json_report_round_trips(self):
        import json
        data = json.loads(self.report().as_json())
        self.assertEqual(data["findings"][0]["klass"], "env-backup")
        self.assertEqual(data["files_scanned"], 3)
        self.assertEqual(data["summary"]["findings"], 1)

    def test_revoke_list_emits_paths_only(self):
        lines = self.report().revoke_list()
        self.assertEqual(lines, ["/r/p/.env.bak.1"])

    def test_revoke_list_deduplicates_paths(self):
        f = Finding(path="/r/p/.env", line=1, pattern_id="x", fingerprint="aaaa",
                    value_len=5, klass="env", signals=())
        g = Finding(path="/r/p/.env", line=9, pattern_id="y", fingerprint="bbbb",
                    value_len=5, klass="env", signals=())
        report = Report(roots=["/r"], findings=[f, g], skipped=[],
                        files_scanned=1, files_skipped=0)
        self.assertEqual(report.revoke_list(), ["/r/p/.env"])

    def test_clean_report_says_clean(self):
        report = Report(roots=["/r"], findings=[], skipped=[],
                        files_scanned=5, files_skipped=0)
        self.assertIn("clean", report.as_text().lower())


if __name__ == "__main__":
    unittest.main()
