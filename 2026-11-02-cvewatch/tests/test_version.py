"""dpkg version ordering. The whole tool hangs on this: '7.0.0-38.38' vs '7.0.0-43.43'
must never be a string compare (string compare says 38 < 43 correctly here, but says
'7.0.0-9.9' > '7.0.0-43.43' wrongly). Pinned pairs below are what dpkg --compare-versions
actually answers; one test cross-checks against the real dpkg when it is installed."""

import shutil
import subprocess
import unittest

from cvewatch.version import compare, is_newer_or_equal, split_version


class SplitTests(unittest.TestCase):
    def test_epoch_upstream_revision(self):
        self.assertEqual(split_version("2:1.0-3ubuntu1"), ("2", "1.0", "3ubuntu1"))

    def test_no_epoch_no_revision(self):
        self.assertEqual(split_version("7.0.0"), ("0", "7.0.0", ""))

    def test_kernel_abi_revision(self):
        self.assertEqual(split_version("7.0.0-38.38"), ("0", "7.0.0", "38.38"))

    def test_revision_with_plus(self):
        self.assertEqual(split_version("7.0.0-38.38+1"), ("0", "7.0.0", "38.38+1"))


class CompareTests(unittest.TestCase):
    def test_kernel_target_is_newer(self):
        self.assertEqual(compare("7.0.0-38.38", "7.0.0-43.43"), -1)

    def test_kernel_target_is_newer_reverse(self):
        self.assertEqual(compare("7.0.0-43.43", "7.0.0-38.38"), 1)

    def test_equal_versions(self):
        self.assertEqual(compare("7.0.0-38.38", "7.0.0-38.38"), 0)

    def test_numeric_not_lexicographic(self):
        # A string compare gets this one wrong; dpkg does not.
        self.assertEqual(compare("7.0.0-9.9", "7.0.0-43.43"), -1)

    def test_tilde_sorts_before_everything(self):
        self.assertEqual(compare("1.0~rc1", "1.0"), -1)
        self.assertEqual(compare("1.0", "1.0~rc1"), 1)

    def test_tilde_sorts_before_empty(self):
        self.assertEqual(compare("1.0~~", "1.0~"), -1)

    def test_epoch_wins_over_upstream(self):
        self.assertEqual(compare("2:1.0", "1:9.9"), 1)

    def test_missing_epoch_is_zero(self):
        self.assertEqual(compare("1.0", "0:1.0"), 0)

    def test_abi_suffix_plus_is_greater(self):
        self.assertEqual(compare("7.0.0-38.38+1", "7.0.0-38.38"), 1)

    def test_letters_sort_before_punctuation(self):
        # dpkg: letters sort before all non-letter characters; 'a' < '+'
        self.assertEqual(compare("1.0a", "1.0+"), -1)

    def test_leading_zeros_are_equal(self):
        self.assertEqual(compare("1.007", "1.7"), 0)

    def test_longer_digit_run_is_greater(self):
        self.assertEqual(compare("1.10", "1.9"), 1)

    def test_is_newer_or_equal(self):
        self.assertTrue(is_newer_or_equal("7.0.0-43.43", "7.0.0-43.43"))
        self.assertTrue(is_newer_or_equal("7.0.0-43.43", "7.0.0-38.38"))
        self.assertFalse(is_newer_or_equal("7.0.0-38.38", "7.0.0-43.43"))


@unittest.skipUnless(shutil.which("dpkg"), "dpkg not installed")
class RealDpkgCrossCheck(unittest.TestCase):
    """Independent oracle: the same pairs answered by dpkg itself."""

    PAIRS = [
        ("7.0.0-38.38", "7.0.0-43.43"),
        ("7.0.0-9.9", "7.0.0-43.43"),
        ("1.0~rc1", "1.0"),
        ("2:1.0", "1:9.9"),
        ("6.8.0-149.149", "7.0.0-43.43"),
        ("5.15.0-203.213", "6.8.0-149.149"),
        ("7.0.0-38.38+1", "7.0.0-38.38"),
        ("24.04", "26.04"),
    ]

    def _dpkg(self, op, a, b):
        return subprocess.run(
            ["dpkg", "--compare-versions", a, op, b],
            capture_output=True, text=True).returncode == 0

    def test_pairs_match_dpkg(self):
        for a, b in self.PAIRS:
            with self.subTest(a=a, b=b):
                ours = compare(a, b)
                if self._dpkg("lt", a, b):
                    self.assertEqual(ours, -1)
                elif self._dpkg("eq", a, b):
                    self.assertEqual(ours, 0)
                elif self._dpkg("gt", a, b):
                    self.assertEqual(ours, 1)
                else:  # pragma: no cover - dpkg cannot order these, nothing to compare
                    self.skipTest("dpkg could not order %r vs %r" % (a, b))


if __name__ == "__main__":
    unittest.main()
