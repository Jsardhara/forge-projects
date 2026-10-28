"""Version parsing and comparison."""

import unittest

from tsattest import semver


class TestParse(unittest.TestCase):
    def test_parses_the_real_host_string(self):
        # The exact long version this host prints: a build suffix after a dash.
        v = semver.parse("1.102.3-t9329c3677-ga522f65e9")
        self.assertEqual((v.major, v.minor, v.patch), (1, 102, 3))
        self.assertIn("t9329c3677", v.build)

    def test_parses_plain_triple(self):
        self.assertEqual(semver.parse("1.104.4"), semver.Version(1, 104, 4))

    def test_parses_surrounding_whitespace_and_leading_v(self):
        self.assertEqual(semver.parse("  v1.104.4 \n"), semver.Version(1, 104, 4))

    def test_build_suffix_does_not_affect_equality(self):
        self.assertEqual(semver.parse("1.104.4-abc"), semver.parse("1.104.4"))

    def test_rejects_non_versions(self):
        for bad in ("", "   ", "abc", "1.2", "1.102.x", "1..3"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    semver.parse(bad)


class TestOrdering(unittest.TestCase):
    def test_below(self):
        self.assertLess(semver.parse("1.102.3"), semver.parse("1.104.4"))

    def test_patch_level_fix_ordering(self):
        # TS-2026-013 is fixed in 1.104.2, before the 1.104.4 batch.
        self.assertLess(semver.parse("1.104.1"), semver.parse("1.104.2"))
        self.assertLess(semver.parse("1.104.2"), semver.parse("1.104.4"))

    def test_boundary_is_inclusive_at_or_above(self):
        self.assertGreaterEqual(semver.parse("1.104.4"), semver.parse("1.104.4"))

    def test_minor_beats_patch(self):
        self.assertLess(semver.parse("1.9.99"), semver.parse("1.10.0"))


if __name__ == "__main__":
    unittest.main()
