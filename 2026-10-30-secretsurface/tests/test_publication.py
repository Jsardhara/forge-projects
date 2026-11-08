"""Publication state: a question only git can answer.

Measured 2026-11-08 against the shipped tool: `in-git-worktree` was a parent-`.git`
existence check, so every finding inside a repo carried an identical signal whether
the file was already committed, one `git add .` from being committed, or excluded.
The signal was true for everything the scanner could see and therefore told nobody
anything. These tests pin the states apart, and pin the one rule that matters more
than any of them: a git we could not ask must never read back as "excluded".

Fixture value is deliberately NOT an AWS documentation key -- `AKIA...EXAMPLE`
contains the word "example" and is dropped by the tool's own placeholder filter,
which would make every test below pass while measuring nothing.
"""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from secretsurface import blast
from secretsurface.blast import blast_signals, publication_rank, publication_state
from secretsurface.classify import CLASSES, classify_path
from secretsurface.scan import scan

AKIA = "AKIA" + "Q2XK7ZP4M9W1TRVB"


def _git(root, *args):
    """Run git as the fixture repo's own identity, ignoring host config."""
    return subprocess.run(
        ["git", "-C", str(root), "-c", "user.email=t@t.t", "-c", "user.name=t"] + list(args),
        capture_output=True, text=True)


class GitRepoCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        _git(self.root, "init", "-q", ".")
        blast._reset_caches()

    def tearDown(self):
        self._tmp.cleanup()
        blast._reset_caches()

    def write(self, rel, body):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body)
        return path

    def commit_all(self):
        _git(self.root, "add", "-A", ".")
        _git(self.root, "commit", "-qm", "fixture")


class PublicationStateTests(GitRepoCase):
    def test_committed_file_is_git_tracked(self):
        path = self.write("app.py", "x = 1\n")
        self.commit_all()
        self.assertEqual(publication_state(path), "git-tracked")

    def test_untracked_file_not_covered_by_ignore_is_untracked_unignored(self):
        path = self.write("scratch.py", "x = 1\n")
        self.assertEqual(publication_state(path), "git-untracked-unignored")

    def test_gitignored_file_is_git_ignored(self):
        self.write(".gitignore", "local.env\n")
        path = self.write("local.env", "AWS_KEY=%s\n" % AKIA)
        self.assertEqual(publication_state(path), "git-ignored")

    def test_tracked_file_stays_tracked_even_when_ignore_pattern_matches(self):
        # Real git keeps tracking a file that is later added to .gitignore.
        path = self.write("pinned.env", "AWS_KEY=%s\n" % AKIA)
        self.commit_all()
        self.write(".gitignore", "pinned.env\n")
        self.assertEqual(publication_state(path), "git-tracked")

    def test_excluded_by_git_info_exclude_is_git_ignored(self):
        # The walker implements .gitignore only; git's own exclude file is a
        # decision the scanner cannot see, so only git's answer is trustworthy.
        (self.root / ".git" / "info").mkdir(parents=True, exist_ok=True)
        (self.root / ".git" / "info" / "exclude").write_text("excluded.env\n")
        path = self.write("excluded.env", "AWS_KEY=%s\n" % AKIA)
        self.assertEqual(publication_state(path), "git-ignored")

    def test_directory_outside_any_repo_is_no_git_worktree(self):
        with tempfile.TemporaryDirectory() as outside:
            path = Path(outside) / "plain.env"
            path.write_text("AWS_KEY=%s\n" % AKIA)
            self.assertEqual(publication_state(path), "no-git-worktree")

    def test_missing_git_binary_is_unknown_never_ignored(self):
        path = self.write("local.env", "AWS_KEY=%s\n" % AKIA)
        with mock.patch.object(blast, "_run_git", return_value=None):
            self.assertEqual(publication_state(path), "git-unknown")

    def test_git_failure_inside_a_worktree_is_unknown_never_ignored(self):
        path = self.write("local.env", "AWS_KEY=%s\n" % AKIA)

        def explode(*_args, **_kwargs):
            return subprocess.CompletedProcess(args=(), returncode=128, stdout="", stderr="boom")

        with mock.patch.object(blast, "_run_git", side_effect=explode):
            self.assertEqual(publication_state(path), "git-unknown")

    def test_git_binary_absent_returns_none_from_run_git(self):
        # The literal "no git installed" path: subprocess raises, not returns.
        path = self.write("local.env", "AWS_KEY=%s\n" % AKIA)
        with mock.patch.object(blast.subprocess, "run", side_effect=FileNotFoundError("git")):
            self.assertIsNone(blast._run_git(self.root, ("status",)))
            self.assertEqual(publication_state(path), "git-unknown")

    def test_unreadable_path_is_unknown(self):
        self.assertEqual(publication_state(self.root / "nope" / "x.env"), "git-unknown")

    def test_state_is_reused_for_repeat_questions_about_one_path(self):
        path = self.write("app.py", "x = 1\n")
        before = blast._git_calls()
        publication_state(path)
        mid = blast._git_calls()
        publication_state(path)
        self.assertGreater(mid, before)
        self.assertEqual(blast._git_calls(), mid)


class SignalTests(GitRepoCase):
    def test_tracked_secret_carries_git_tracked_signal(self):
        path = self.write("app.py", "AWS_KEY=%s\n" % AKIA)
        self.commit_all()
        self.assertIn("git-tracked", blast_signals(path, "unknown"))

    def test_ignored_secret_carries_git_ignored_signal(self):
        self.write(".gitignore", "local.env\n")
        path = self.write("local.env", "AWS_KEY=%s\n" % AKIA)
        self.assertIn("git-ignored", blast_signals(path, "env"))

    def test_in_git_worktree_is_retired_as_a_blast_signal(self):
        path = self.write("app.py", "AWS_KEY=%s\n" % AKIA)
        self.commit_all()
        self.assertNotIn("in-git-worktree", blast_signals(path, "unknown"))

    def test_exactly_one_publication_signal_is_emitted(self):
        path = self.write("app.py", "AWS_KEY=%s\n" % AKIA)
        self.commit_all()
        found = [s for s in blast_signals(path, "env") if s.startswith(("git-", "no-git"))]
        self.assertEqual(len(found), 1)


class RankingTests(GitRepoCase):
    def test_tracked_ranks_above_untracked_above_ignored(self):
        self.assertLess(publication_rank(("git-tracked",)),
                        publication_rank(("git-untracked-unignored",)))
        self.assertLess(publication_rank(("git-untracked-unignored",)),
                        publication_rank(("git-ignored",)))

    def test_unknown_ranks_above_ignored_so_it_never_reads_as_safe(self):
        self.assertLess(publication_rank(("git-unknown",)), publication_rank(("git-ignored",)))

    def test_missing_signal_ranks_as_unknown(self):
        self.assertEqual(publication_rank(()), publication_rank(("git-unknown",)))


class CommittedConfigClassTests(GitRepoCase):
    def test_class_is_declared_before_unknown(self):
        self.assertIn("committed-config", CLASSES)
        self.assertLess(CLASSES.index("committed-config"), CLASSES.index("unknown"))

    def test_claude_local_settings_is_committed_config(self):
        self.assertEqual(
            classify_path("/repo/.claude/settings.local.json"), "committed-config")

    def test_claude_settings_json_is_committed_config(self):
        self.assertEqual(classify_path("/repo/.claude/settings.json"), "committed-config")

    def test_mcp_json_is_committed_config(self):
        self.assertEqual(classify_path("/repo/.mcp.json"), "committed-config")

    def test_cursor_rules_are_committed_config(self):
        self.assertEqual(classify_path("/repo/.cursor/rules.md"), "committed-config")

    def test_agents_md_is_committed_config_not_a_doc_fixture(self):
        self.assertEqual(classify_path("/repo/AGENTS.md"), "committed-config")

    def test_aider_config_is_committed_config(self):
        self.assertEqual(classify_path("/repo/.aider.conf.yml"), "committed-config")

    def test_env_is_still_env(self):
        self.assertEqual(classify_path("/repo/.env"), "env")

    def test_env_backup_is_still_env_backup(self):
        self.assertEqual(classify_path("/repo/.env.bak"), "env-backup")

    def test_unrelated_json_is_still_unknown(self):
        self.assertEqual(classify_path("/repo/config.json"), "unknown")


class EndToEndOrderingTests(GitRepoCase):
    def test_published_config_sorts_above_an_unpublished_backup(self):
        # Published-ness outranks class: a tracked committed config must come
        # before a superseded backup that git has never seen.
        self.write(".claude/settings.local.json", '{"a": "AWS_KEY=%s"}\n' % AKIA)
        self.commit_all()
        self.write(".env.bak", "AWS_KEY=%s\n" % AKIA)
        report = scan([self.root])
        paths = [f.path for f in report.findings]
        self.assertEqual(len(paths), 2)
        self.assertTrue(paths[0].endswith("settings.local.json"))
        self.assertTrue(paths[1].endswith(".env.bak"))
        self.assertEqual(report.findings[0].klass, "committed-config")
        self.assertEqual(report.findings[1].klass, "env-backup")

    def test_file_git_excludes_but_the_walker_reads_sorts_last(self):
        # Reachable overstatement: the walker reads .git/info/exclude? No -- it only
        # implements .gitignore, so this file IS scanned. Git says it cannot be
        # published; the report must say so and rank it last.
        (self.root / ".git" / "info").mkdir(parents=True, exist_ok=True)
        (self.root / ".git" / "info" / "exclude").write_text("-excluded.env\n")
        self.write("-excluded.env", "AWS_KEY=%s\n" % AKIA)
        tracked = self.write(".claude/settings.local.json", '{"a": "AWS_KEY=%s"}\n' % AKIA)
        self.commit_all()

        report = scan([self.root])
        paths = [f.path for f in report.findings]
        self.assertEqual(len(paths), 2)
        self.assertEqual(paths[0], str(tracked))
        self.assertTrue(paths[-1].endswith("-excluded.env"))
        self.assertIn("git-ignored", report.findings[-1].signals)

    def test_verdict_and_exit_code_are_unchanged_by_the_ordering(self):
        self.write("app.py", "AWS_KEY=%s\n" % AKIA)
        self.commit_all()
        report = scan([self.root])
        self.assertEqual(report.exit_code(), 1)
        self.assertFalse(report.is_clean())


if __name__ == "__main__":
    unittest.main()
