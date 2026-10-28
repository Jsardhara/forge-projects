"""Bulletin table and applicability evaluation."""

import unittest

from tsattest import bulletins
from tsattest.bulletins import Facts
from tsattest.semver import parse


def facts(version="1.102.3", ssh=True, serve=True, serve_unix=False, mounts=1,
          tls=True):
    return Facts(version=parse(version) if version else None,
                 ssh_enabled=ssh,
                 serve_present=serve,
                 serve_unix_backend=serve_unix,
                 serve_mounts=mounts,
                 serve_tls=tls)


def by_key(results):
    return {r.key: r for r in results}


class TestTableShape(unittest.TestCase):
    def test_all_five_bulletins_present(self):
        keys = [b.key for b in bulletins.BULLETINS]
        self.assertEqual(keys, ["TS-2026-013", "TS-2026-014", "TS-2026-015",
                                "TS-2026-016", "TS-2026-017"])

    def test_fix_versions_are_the_published_ones(self):
        fixed = {b.key: b.fixed_in for b in bulletins.BULLETINS}
        self.assertEqual(fixed["TS-2026-013"], "1.104.2")
        self.assertEqual(fixed["TS-2026-014"], "1.104.4")
        self.assertEqual(fixed["TS-2026-015"], "1.104.4")
        self.assertEqual(fixed["TS-2026-016"], "1.104.4")
        self.assertEqual(fixed["TS-2026-017"], "1.104.4")


class TestApplicability(unittest.TestCase):
    def test_this_host_shape_opens_the_expected_set(self):
        # The real shape measured on 2026-10-28: 1.102.3, SSH on, one serve mount,
        # http proxy backend (not unix), TLS on.
        r = by_key(bulletins.evaluate(facts(serve_unix=False, mounts=1)))
        self.assertEqual(r["TS-2026-013"].status, bulletins.OPEN)
        self.assertEqual(r["TS-2026-014"].status, bulletins.OPEN)
        self.assertEqual(r["TS-2026-015"].status, bulletins.OPEN)
        self.assertEqual(r["TS-2026-016"].status, bulletins.NOT_APPLICABLE)
        # The advisory requires at least TWO mounts with different capabilities.
        self.assertEqual(r["TS-2026-017"].status, bulletins.NOT_APPLICABLE)

    def test_017_applies_only_with_two_or_more_mounts(self):
        one = by_key(bulletins.evaluate(facts(mounts=1)))
        two = by_key(bulletins.evaluate(facts(mounts=2)))
        self.assertEqual(one["TS-2026-017"].status, bulletins.NOT_APPLICABLE)
        self.assertEqual(two["TS-2026-017"].status, bulletins.OPEN)

    def test_017_needs_tls(self):
        r = by_key(bulletins.evaluate(facts(mounts=3, tls=False)))
        self.assertEqual(r["TS-2026-017"].status, bulletins.NOT_APPLICABLE)

    def test_017_with_unreadable_mount_count_is_unknown(self):
        r = by_key(bulletins.evaluate(facts(mounts=None)))
        self.assertEqual(r["TS-2026-017"].status, bulletins.UNKNOWN)
        self.assertNotEqual(r["TS-2026-017"].status, bulletins.NOT_APPLICABLE)

    def test_ssh_off_makes_ssh_bulletins_not_applicable(self):
        r = by_key(bulletins.evaluate(facts(ssh=False)))
        self.assertEqual(r["TS-2026-014"].status, bulletins.NOT_APPLICABLE)
        self.assertEqual(r["TS-2026-015"].status, bulletins.NOT_APPLICABLE)
        self.assertEqual(r["TS-2026-013"].status, bulletins.OPEN)

    def test_serve_absent_makes_serve_bulletins_not_applicable(self):
        r = by_key(bulletins.evaluate(facts(serve=False)))
        self.assertEqual(r["TS-2026-016"].status, bulletins.NOT_APPLICABLE)
        self.assertEqual(r["TS-2026-017"].status, bulletins.NOT_APPLICABLE)

    def test_unix_serve_backend_makes_016_apply(self):
        r = by_key(bulletins.evaluate(facts(serve=True, serve_unix=True)))
        self.assertEqual(r["TS-2026-016"].status, bulletins.OPEN)


class TestUnmeasurableIsNotNotApplicable(unittest.TestCase):
    def test_unknown_ssh_state_makes_ssh_bulletins_unknown(self):
        r = by_key(bulletins.evaluate(facts(ssh=None)))
        self.assertEqual(r["TS-2026-014"].status, bulletins.UNKNOWN)
        self.assertEqual(r["TS-2026-015"].status, bulletins.UNKNOWN)
        self.assertNotEqual(r["TS-2026-014"].status, bulletins.NOT_APPLICABLE)

    def test_unknown_serve_state_makes_serve_bulletins_unknown(self):
        r = by_key(bulletins.evaluate(facts(serve=None)))
        self.assertEqual(r["TS-2026-017"].status, bulletins.UNKNOWN)

    def test_unknown_version_makes_everything_unknown(self):
        r = bulletins.evaluate(facts(version=None))
        self.assertTrue(all(x.status == bulletins.UNKNOWN for x in r))
        self.assertEqual(len(r), 5)


class TestFixBoundaries(unittest.TestCase):
    def test_mid_span_fix(self):
        # 1.104.3 is past the 013 fix (1.104.2) but before the 1.104.4 batch.
        r = by_key(bulletins.evaluate(facts(version="1.104.3")))
        self.assertEqual(r["TS-2026-013"].status, bulletins.CLOSED)
        self.assertEqual(r["TS-2026-015"].status, bulletins.OPEN)

    def test_exactly_the_fix_version_is_closed(self):
        # unix backend + 2 TLS mounts so every bulletin is applicable: all CLOSED.
        r = by_key(bulletins.evaluate(facts(version="1.104.4", serve_unix=True,
                                            mounts=2)))
        self.assertTrue(all(x.status == bulletins.CLOSED for x in r.values()))

    def test_exactly_the_fix_version_closes_what_applies(self):
        r = by_key(bulletins.evaluate(facts(version="1.104.4", serve_unix=False,
                                            mounts=1)))
        self.assertEqual(r["TS-2026-016"].status, bulletins.NOT_APPLICABLE)
        self.assertEqual(r["TS-2026-017"].status, bulletins.NOT_APPLICABLE)
        self.assertEqual(r["TS-2026-013"].status, bulletins.CLOSED)
        self.assertEqual(r["TS-2026-014"].status, bulletins.CLOSED)
        self.assertEqual(r["TS-2026-015"].status, bulletins.CLOSED)

    def test_exactly_the_earlier_fix_version_is_closed(self):
        r = by_key(bulletins.evaluate(facts(version="1.104.2")))
        self.assertEqual(r["TS-2026-013"].status, bulletins.CLOSED)
        self.assertEqual(r["TS-2026-014"].status, bulletins.OPEN)


class TestVerdict(unittest.TestCase):
    def test_any_open_is_fail(self):
        self.assertEqual(bulletins.verdict(bulletins.evaluate(facts())), "FAIL")

    def test_all_closed_is_pass(self):
        self.assertEqual(bulletins.verdict(
            bulletins.evaluate(facts(version="1.104.4"))), "PASS")

    def test_no_open_but_unknown_is_unknown(self):
        self.assertEqual(bulletins.verdict(
            bulletins.evaluate(facts(version="1.104.4", serve=None))), "UNKNOWN")

    def test_not_applicable_alone_does_not_block_a_pass(self):
        v = bulletins.verdict(bulletins.evaluate(
            facts(version="1.104.4", ssh=False, serve=False)))
        self.assertEqual(v, "PASS")

    def test_exit_codes_are_distinct_and_fail_closed(self):
        self.assertEqual(bulletins.exit_code("PASS"), 0)
        self.assertEqual(bulletins.exit_code("FAIL"), 1)
        self.assertEqual(bulletins.exit_code("UNKNOWN"), 2)
        # UNKNOWN must never collapse into PASS's 0.
        self.assertNotEqual(bulletins.exit_code("UNKNOWN"), 0)


if __name__ == "__main__":
    unittest.main()
