import unittest

from decoderattest.version import (
    VersionError,
    base,
    compare,
    is_below,
    parse,
)


class ParseTests(unittest.TestCase):
    def test_plain_three_part(self):
        self.assertEqual(parse("26.8.2"), (26, 8, 2))

    def test_four_part_wheel_version(self):
        self.assertEqual(parse("1.2.1.0"), (1, 2, 1, 0))

    def test_leading_v_prefix(self):
        self.assertEqual(parse("v1.2.1"), (1, 2, 1))

    def test_debian_revision_is_dropped_from_base(self):
        self.assertEqual(base("1.2.0-3build1"), (1, 2, 0))

    def test_plus_local_segment_is_dropped(self):
        self.assertEqual(base("2.14.0+cu130"), (2, 14, 0))

    def test_garbage_raises(self):
        with self.assertRaises(VersionError):
            parse("not-a-version")

    def test_empty_raises(self):
        with self.assertRaises(VersionError):
            parse("")

    def test_trailing_dot_raises(self):
        with self.assertRaises(VersionError):
            parse("1.2.")


class CompareTests(unittest.TestCase):
    def test_different_lengths_pad_with_zero(self):
        self.assertEqual(compare("1.2", "1.2.0"), 0)

    def test_numeric_not_lexicographic(self):
        # Plain string order puts "26.8.2" AFTER "26.12.1" ('8' > '1'); the
        # advisory's fix boundary is the opposite, so component compare is required.
        self.assertLess(compare("26.8.2", "26.12.1"), 0)
        self.assertGreater("26.8.2", "26.12.1")

    def test_greater(self):
        self.assertGreater(compare("1.2.1", "1.2.0"), 0)

    def test_is_below(self):
        self.assertTrue(is_below("26.8.2", "26.12.1"))
        self.assertFalse(is_below("26.12.1", "26.12.1"))

    def test_debian_revision_ignored_in_compare(self):
        self.assertEqual(compare("1.2.0-3build1", "1.2.0"), 0)

    def test_bad_version_in_compare_raises(self):
        with self.assertRaises(VersionError):
            compare("1.2.x", "1.2.0")


if __name__ == "__main__":
    unittest.main()
