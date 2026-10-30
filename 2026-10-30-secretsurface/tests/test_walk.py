"""Tests for the filesystem walk: dotdirs are the point, .gitignore is honoured."""
import os
import tempfile
import unittest
from pathlib import Path

from secretsurface.walk import scan_tree, read_text


class WalkTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, rel, content="x\n"):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def test_dot_directories_are_not_skipped(self):
        # the whole premise: the leak is inside .curator_backups/
        self.write(".curator_backups/blobs/ab12", "value\n")
        files, _ = scan_tree([self.root])
        names = [p.relative_to(self.root).as_posix() for p in files]
        self.assertIn(".curator_backups/blobs/ab12", names)

    def test_plain_files_are_found(self):
        self.write("plain.txt")
        files, _ = scan_tree([self.root])
        self.assertEqual(len(files), 1)

    def test_git_dir_is_skipped_and_reported(self):
        self.write(".git/config", "[core]\n")
        self.write("keep.txt")
        files, skipped = scan_tree([self.root])
        names = [p.relative_to(self.root).as_posix() for p in files]
        self.assertNotIn(".git/config", names)
        self.assertIn("keep.txt", names)
        self.assertTrue(any("vcs" in reason for _, reason in skipped))

    def test_pycache_is_skipped_and_reported(self):
        self.write("__pycache__/x.pyc", "junk")
        self.write("keep.txt")
        files, skipped = scan_tree([self.root])
        self.assertEqual([p.name for p in files], ["keep.txt"])
        self.assertTrue(skipped)

    def test_gitignore_glob_excludes_matching_file(self):
        self.write(".gitignore", "*.log\n")
        self.write("secret.log", "key\n")
        self.write("keep.txt")
        files, _ = scan_tree([self.root])
        self.assertEqual([p.name for p in files], ["keep.txt"])

    def test_gitignore_negation_reincludes(self):
        self.write(".gitignore", "*.log\n!keep.log\n")
        self.write("drop.log")
        self.write("keep.log")
        files, _ = scan_tree([self.root])
        self.assertEqual([p.name for p in files], ["keep.log"])

    def test_gitignore_directory_rule_excludes_subtree(self):
        self.write(".gitignore", "vendor/\n")
        self.write("vendor/inner.txt")
        self.write("keep.txt")
        files, _ = scan_tree([self.root])
        self.assertEqual([p.name for p in files], ["keep.txt"])

    def test_gitignored_skips_are_reported_with_a_reason(self):
        self.write(".gitignore", "*.log\n")
        self.write("secret.log")
        _, skipped = scan_tree([self.root])
        self.assertTrue(any("gitignore" in reason for _, reason in skipped))

    def test_binary_file_is_skipped_and_reported(self):
        (self.root / "blob.bin").write_bytes(b"\x00\x01\x02binary")
        self.write("keep.txt")
        files, skipped = scan_tree([self.root])
        self.assertEqual([p.name for p in files], ["keep.txt"])
        self.assertTrue(any("binary" in reason for _, reason in skipped))

    def test_oversized_file_is_skipped_and_reported(self):
        (self.root / "big.txt").write_text("a" * 5000, encoding="utf-8")
        files, skipped = scan_tree([self.root], max_bytes=1000)
        self.assertEqual(files, [])
        self.assertTrue(any("size" in reason for _, reason in skipped))

    def test_missing_root_is_reported_as_unmeasurable_not_clean(self):
        files, skipped = scan_tree([self.root / "does-not-exist"])
        self.assertEqual(files, [])
        self.assertTrue(any("root-missing" in reason for _, reason in skipped))

    def test_results_are_sorted_and_deterministic(self):
        self.write("b.txt")
        self.write("a.txt")
        first, _ = scan_tree([self.root])
        second, _ = scan_tree([self.root])
        self.assertEqual([str(p) for p in first], [str(p) for p in second])
        self.assertEqual([p.name for p in first], ["a.txt", "b.txt"])

    def test_nested_gitignore_applies_to_its_own_subtree_only(self):
        self.write(".gitignore", "*.log\n")
        self.write("sub/.gitignore", "!*.log\n")
        self.write("sub/inside.log")
        self.write("outside.log")
        files, _ = scan_tree([self.root])
        names = sorted(p.relative_to(self.root).as_posix() for p in files)
        self.assertEqual(names, ["sub/inside.log"])


class ReadTextTests(unittest.TestCase):
    def test_reads_utf8(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "f.txt"
            path.write_text("héllo\n", encoding="utf-8")
            self.assertEqual(read_text(path), "héllo\n")

    def test_invalid_bytes_do_not_raise(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "f.bin"
            path.write_bytes(b"abc\xff\xfe def")
            self.assertIsInstance(read_text(path), str)

    def test_read_text_reports_none_on_unreadable_file(self):
        self.assertIsNone(read_text(Path("/proc/1/mem-does-not-exist")))


if __name__ == "__main__":
    unittest.main()
