"""Tests for hit classification: what KIND of store does this file represent."""
import unittest

from secretsurface.classify import CLASSES, classify_path


class EnvTests(unittest.TestCase):
    def test_plain_env_file_is_env(self):
        self.assertEqual(classify_path("profiles/forge/.env"), "env")

    def test_env_local_is_still_a_live_env(self):
        self.assertEqual(classify_path("profiles/forge/.env.local"), "env")

    def test_env_bak_is_env_backup(self):
        self.assertEqual(
            classify_path("profiles/forge/.env.bak.si09-20260911"), "env-backup")

    def test_env_old_and_orig_are_env_backup(self):
        self.assertEqual(classify_path("x/.env.old"), "env-backup")
        self.assertEqual(classify_path("x/.env.orig"), "env-backup")

    def test_env_example_is_a_doc_fixture_not_a_backup(self):
        self.assertEqual(classify_path("x/.env.example"), "doc-fixture")
        self.assertEqual(classify_path("x/.env.sample"), "doc-fixture")
        self.assertEqual(classify_path("x/.env.template"), "doc-fixture")


class StoreKindTests(unittest.TestCase):
    def test_curator_backup_blob_is_backup_blob(self):
        self.assertEqual(
            classify_path("profiles/forge/.curator_backups/blobs/ab12cd34"),
            "backup-blob")

    def test_generic_backup_directory_is_backup_blob(self):
        self.assertEqual(classify_path("some/backups/keys.txt"), "backup-blob")

    def test_tilde_and_bak_suffix_are_backup_blob(self):
        self.assertEqual(classify_path("x/config.json~"), "backup-blob")
        self.assertEqual(classify_path("x/settings.bak"), "backup-blob")

    def test_jsonl_activity_log_is_log_leak(self):
        self.assertEqual(
            classify_path("profiles/sentinel/foreman_activity.jsonl"), "log-leak")

    def test_dot_log_is_log_leak(self):
        self.assertEqual(classify_path("var/app.log"), "log-leak")

    def test_markdown_under_skills_is_doc_fixture(self):
        self.assertEqual(
            classify_path("skills/devops/native-mcp.md"), "doc-fixture")

    def test_test_file_is_doc_fixture(self):
        self.assertEqual(classify_path("tests/test_probes.py"), "doc-fixture")

    def test_unrecognised_store_is_unknown_never_silently_safe(self):
        self.assertEqual(classify_path("random/notes-for-me"), "unknown")

    def test_unknown_is_a_declared_class(self):
        self.assertIn("unknown", CLASSES)


class OrderingTests(unittest.TestCase):
    def test_env_backup_wins_over_generic_backup(self):
        # .env.bak.* lives in neither a backups/ dir nor .curator_backups, but if
        # it ever did, the env-specific reading is the more useful one.
        self.assertEqual(
            classify_path("profiles/forge/backups/.env.bak.si09"), "env-backup")

    def test_log_beats_doc_when_both_would_apply(self):
        # an activity log named *.jsonl inside a skills dir is still a log
        self.assertEqual(
            classify_path("skills/x/foreman_activity.jsonl"), "log-leak")

    def test_every_class_is_reachable(self):
        probes = {
            "env": "a/.env",
            "env-backup": "a/.env.bak.1",
            "log-leak": "a/x.jsonl",
            "backup-blob": "a/.curator_backups/blobs/z",
            "doc-fixture": "a/README.md",
            "unknown": "a/thing",
        }
        for expected, path in probes.items():
            self.assertEqual(classify_path(path), expected, path)


if __name__ == "__main__":
    unittest.main()
