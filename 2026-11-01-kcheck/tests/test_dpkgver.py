"""Debian/Ubuntu version comparison at the boundaries this tool actually meets.

The whole tool rests on this: `7.0.0-38` vs `7.0.0-43.43` is a *string* comparison
that says "38" > "43.43"?  No -- but `7.0.0-9` vs `7.0.0-10` is the classic case where
a naive lexicographic compare says 9 > 10 and reports a vulnerable host as patched.
"""

import unittest

from kcheck import dpkgver


class TestUpstreamVersions(unittest.TestCase):
    def test_tilde_sorts_before_everything(self):
        self.assertLess(dpkgver.compare("1.0~rc1", "1.0"), 0)
        self.assertLess(dpkgver.compare("1.0~~", "1.0~"), 0)

    def test_numeric_segments_compare_numerically(self):
        self.assertLess(dpkgver.compare("1.9", "1.10"), 0)
        self.assertGreater(dpkgver.compare("1.10", "1.9"), 0)
        self.assertGreater(dpkgver.compare("6.6.159", "6.6.99"), 0)

    def test_letters_sort_before_non_letters(self):
        # dpkg: 'a' < '' is false; letters sort before punctuation, after nothing.
        self.assertLess(dpkgver.compare("1.0a", "1.0+"), 0)

    def test_equal_except_zeros(self):
        self.assertEqual(dpkgver.compare("1.0.0", "1.0.0"), 0)
        self.assertEqual(dpkgver.compare("1.00", "1.0"), 0)


class TestEpochAndRevision(unittest.TestCase):
    def test_epoch_dominates(self):
        self.assertGreater(dpkgver.compare("1:0.1", "9.9"), 0)
        self.assertLess(dpkgver.compare("0:9.9", "1:0.1"), 0)

    def test_revision_breaks_upstream_ties(self):
        self.assertGreater(dpkgver.compare("1.0-2", "1.0-1"), 0)
        self.assertEqual(dpkgver.compare("1.0", "1.0-0"), 0)

    def test_abi_suffix_is_compared_not_string_matched(self):
        self.assertLess(dpkgver.compare("7.0.0-38.38", "7.0.0-43.43"), 0)
        self.assertGreater(dpkgver.compare("7.0.0-44", "7.0.0-43.43"), 0)
        self.assertGreater(dpkgver.compare("7.0.0-43.43", "7.0.0-38.38"), 0)
        self.assertEqual(dpkgver.compare("7.0.0-43.43", "7.0.0-43.43"), 0)

    def test_abi_44_38_regression(self):
        # The card's two acceptance boundaries, stated as the tool must see them.
        self.assertLess(dpkgver.compare("7.0.0-38", "7.0.0-43.43"), 0)
        self.assertGreater(dpkgver.compare("7.0.0-44", "7.0.0-43.43"), 0)


class TestParsing(unittest.TestCase):
    def test_split_epoch_upstream_revision(self):
        self.assertEqual(dpkgver.split_version("1:2.3.4-5ubuntu6"), (1, "2.3.4", "5ubuntu6"))
        self.assertEqual(dpkgver.split_version("7.0.0-43.43"), (0, "7.0.0", "43.43"))
        self.assertEqual(dpkgver.split_version("5.10.272"), (0, "5.10.272", ""))

    def test_release_to_version_strips_flavour(self):
        self.assertEqual(dpkgver.release_to_version("7.0.0-38-generic"), "7.0.0-38")
        self.assertEqual(dpkgver.release_to_version("6.8.0-31-lowlatency"), "6.8.0-31")
        self.assertEqual(dpkgver.release_to_version("7.0.0-38-generic\n"), "7.0.0-38")

    def test_release_to_version_leaves_unknown_shapes_alone(self):
        self.assertEqual(dpkgver.release_to_version("6.6.159"), "6.6.159")

    def test_abi_of_kernel_version(self):
        self.assertEqual(dpkgver.abi("7.0.0-38.38"), 38)
        self.assertEqual(dpkgver.abi("7.0.0-43.43"), 43)
        self.assertEqual(dpkgver.abi("7.0.0-44"), 44)
        self.assertIsNone(dpkgver.abi("6.6.159"))

    def test_gap_counts_abi_levels(self):
        self.assertEqual(dpkgver.abi_gap("7.0.0-38.38", "7.0.0-43.43"), 5)
        self.assertEqual(dpkgver.abi_gap("7.0.0-44", "7.0.0-43.43"), -1)
        # An upstream-version jump is not an ABI gap and must not be reported as one.
        self.assertIsNone(dpkgver.abi_gap("6.6.159", "7.0.0-43.43"))

    def test_rejects_garbage(self):
        with self.assertRaises(dpkgver.VersionError):
            dpkgver.compare("", "1.0")
        with self.assertRaises(dpkgver.VersionError):
            dpkgver.compare("7.0.0-38", "  ")


class TestBoundaryTable(unittest.TestCase):
    """A table, not a pile of assertions: the acceptance cases in one place."""

    CASES = (
        # (installed, fixed, expected_lower)
        ("7.0.0-38", "7.0.0-43.43", True),
        ("7.0.0-38.38", "7.0.0-43.43", True),
        ("7.0.0-43.42", "7.0.0-43.43", True),
        ("7.0.0-43.43", "7.0.0-43.43", False),
        ("7.0.0-43.44", "7.0.0-43.43", False),
        ("7.0.0-44", "7.0.0-43.43", False),
        ("5.10.271", "5.10.272", True),
        ("6.6.159", "6.6.159", False),
        ("4.3", "4.4", True),
    )

    def test_table(self):
        for installed, fixed, expected_lower in self.CASES:
            with self.subTest(installed=installed, fixed=fixed):
                self.assertEqual(dpkgver.compare(installed, fixed) < 0, expected_lower)


if __name__ == "__main__":
    unittest.main()
