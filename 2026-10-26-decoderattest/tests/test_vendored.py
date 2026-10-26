import os
import unittest

from decoderattest.vendored import scan_tree
from support import TmpTree, make_vendored_tree, write


class ScanTreeTests(unittest.TestCase):
    def test_finds_nested_decode_header(self):
        with TmpTree() as root:
            make_vendored_tree(root, version=(1, 2, 0), patched=False)
            copies = scan_tree(root)
        self.assertEqual(len(copies), 1)
        self.assertTrue(copies[0].header.endswith(os.path.join("brotli", "decode.h")))

    def test_reads_version_macros_not_the_cve_span(self):
        with TmpTree() as root:
            make_vendored_tree(root, version=(1, 2, 0), patched=False)
            copy = scan_tree(root)[0]
        self.assertEqual(copy.version, "1.2.0")

    def test_unpatched_copy_lacks_block_switch(self):
        with TmpTree() as root:
            make_vendored_tree(root, version=(1, 2, 0), patched=False)
            copy = scan_tree(root)[0]
        self.assertFalse(copy.has_block_switch)

    def test_patched_copy_has_block_switch(self):
        with TmpTree() as root:
            make_vendored_tree(root, version=(1, 2, 1), patched=True)
            copy = scan_tree(root)[0]
        self.assertTrue(copy.has_block_switch)

    def test_signals_agree_for_consistent_copies(self):
        with TmpTree() as root:
            make_vendored_tree(root, version=(1, 2, 0), patched=False)
            self.assertTrue(scan_tree(root)[0].signals_agree)
        with TmpTree() as root:
            make_vendored_tree(root, version=(1, 2, 1), patched=True)
            self.assertTrue(scan_tree(root)[0].signals_agree)

    def test_version_says_patched_but_marker_missing_is_a_disagreement(self):
        # A copy whose version.h was bumped without the fix landing is exactly the
        # failure a single-signal check certifies as safe.
        with TmpTree() as root:
            make_vendored_tree(root, version=(1, 2, 1), patched=False)
            copy = scan_tree(root)[0]
        self.assertFalse(copy.signals_agree)

    def test_unversioned_copy_still_scanned(self):
        with TmpTree() as root:
            make_vendored_tree(root, with_version_h=False, patched=False)
            copy = scan_tree(root)[0]
        self.assertIsNone(copy.version)
        self.assertFalse(copy.has_block_switch)

    def test_empty_tree_yields_nothing(self):
        with TmpTree() as root:
            write(os.path.join(root, "README.md"), "nothing here\n")
            self.assertEqual(scan_tree(root), [])

    def test_missing_path_is_loud(self):
        with self.assertRaises(OSError):
            scan_tree("/nonexistent/vendor/tree")

    def test_git_dir_is_skipped(self):
        with TmpTree() as root:
            make_vendored_tree(root)
            write(os.path.join(root, ".git", "objects", "brotli", "decode.h"), "x\n")
            self.assertEqual(len(scan_tree(root)), 1)

    def test_two_copies_are_both_reported(self):
        with TmpTree() as root:
            make_vendored_tree(root, version=(1, 2, 0), patched=False)
            other = os.path.join(root, "other-vendor", "brotli", "c")
            write(
                os.path.join(other, "include", "brotli", "decode.h"),
                "BROTLI_ERROR_CODE(_ERROR_FORMAT_, BLOCK_SWITCH, -17)\n",
            )
            copies = scan_tree(root)
        self.assertEqual(len(copies), 2)
        versions = sorted(str(c.version) for c in copies)
        self.assertEqual(versions, ["1.2.0", "None"])


if __name__ == "__main__":
    unittest.main()
