"""The two axes are separate on purpose: in range and on the demonstrated path are
different claims, and the second one never softens the first.
"""

import unittest

import helpers
from kcheck import assess, host, table


def facts(**kwargs):
    base = dict(
        release="7.0.0-38-generic",
        package_name="linux-image-7.0.0-38-generic",
        package_version="7.0.0-38.38",
        kernel_images=("linux-image-7.0.0-38-generic",),
        mptcp_enabled=True,
        mptcp_listeners=host.parse_ss(helpers.SS_TAILNET),
        distro="ubuntu",
        distro_release="26.04",
        distro_codename="resolute",
        errors=(),
    )
    base.update(kwargs)
    return host.HostFacts(**base)


def load(doc=None):
    return table.from_dict(doc or helpers.table_doc())


class TestFixPending(unittest.TestCase):
    """Ubuntu's row today: range known, fix not released. Exit 1, not 0 and not 2."""

    def setUp(self):
        self.finding = assess.assess_cve(load().get("CVE-2026-98432"), facts())

    def test_in_range(self):
        self.assertTrue(self.finding.in_range)

    def test_verdict_is_vulnerable_and_state_is_fix_pending(self):
        self.assertEqual(self.finding.verdict, assess.VULNERABLE)
        self.assertEqual(self.finding.fix_state, table.FIX_PENDING)

    def test_reports_the_running_kernel_and_the_target(self):
        self.assertEqual(self.finding.installed_version, "7.0.0-38.38")
        self.assertEqual(self.finding.fixed_version, "7.0.0-43.43")

    def test_abi_gap(self):
        self.assertEqual(self.finding.abi_gap, 5)

    def test_on_path_because_mptcp_is_on_and_listening(self):
        self.assertIs(self.finding.on_demonstrated_path, True)

    def test_exposure_is_tailnet_and_localhost(self):
        self.assertEqual(self.finding.exposure_surface, ("tailnet", "localhost"))

    def test_carries_provenance(self):
        self.assertEqual(self.finding.source_url, "https://ubuntu.com/security/CVE-2026-98432")
        self.assertEqual(self.finding.retrieved_at, "2026-11-01T06:26:00Z")


class TestReleasedFix(unittest.TestCase):
    def test_below_released_fix_is_vulnerable(self):
        doc = helpers.table_doc(fix_state=table.FIX_RELEASED, fixed_version="7.0.0-43.43")
        f = assess.assess_cve(load(doc).get("CVE-2026-98432"), facts())
        self.assertEqual(f.verdict, assess.VULNERABLE)
        self.assertTrue(f.in_range)

    def test_at_released_fix_is_fixed(self):
        doc = helpers.table_doc(fix_state=table.FIX_RELEASED, fixed_version="7.0.0-38.38")
        f = assess.assess_cve(load(doc).get("CVE-2026-98432"), facts())
        self.assertEqual(f.verdict, assess.FIXED)
        self.assertFalse(f.in_range)

    def test_above_released_fix_is_fixed(self):
        doc = helpers.table_doc(fix_state=table.FIX_RELEASED, fixed_version="7.0.0-43.43")
        f = assess.assess_cve(load(doc).get("CVE-2026-98432"),
                              facts(release="7.0.0-44-generic", package_version="7.0.0-44.44"))
        self.assertEqual(f.verdict, assess.FIXED)

    def test_fixed_host_is_still_on_path_if_listening(self):
        # "Not vulnerable" does not mean "not exposed" -- the two axes stay independent.
        doc = helpers.table_doc(fix_state=table.FIX_RELEASED, fixed_version="7.0.0-38.38")
        f = assess.assess_cve(load(doc).get("CVE-2026-98432"), facts())
        self.assertFalse(f.in_range)
        self.assertIs(f.on_demonstrated_path, True)


class TestUnknown(unittest.TestCase):
    def test_unknown_distro_is_unmeasurable(self):
        f = assess.assess_cve(load().get("CVE-2026-98432"), facts(distro="arch", distro_release=""))
        self.assertEqual(f.verdict, assess.UNKNOWN)
        self.assertIsNone(f.in_range)
        self.assertEqual(f.reason, assess.REASON_NO_DISTRO_ROW)

    def test_known_distro_not_in_this_cve_is_unmeasurable(self):
        f = assess.assess_cve(load().get("CVE-2026-98432"),
                              facts(distro="ubuntu", distro_release="24.04"))
        self.assertEqual(f.verdict, assess.UNKNOWN)

    def test_no_installed_version_is_unmeasurable_even_if_row_exists(self):
        f = assess.assess_cve(load().get("CVE-2026-98432"),
                              facts(release=None, package_name=None, package_version=None))
        self.assertEqual(f.verdict, assess.UNKNOWN)
        self.assertEqual(f.reason, assess.REASON_NO_INSTALLED_VERSION)

    def test_unreadable_mptcp_is_none_not_false(self):
        f = assess.assess_cve(load().get("CVE-2026-98432"),
                              facts(mptcp_enabled=None, mptcp_listeners=None))
        self.assertIsNone(f.on_demonstrated_path)
        self.assertTrue(f.in_range)  # the range axis is unaffected

    def test_not_affected_row(self):
        doc = helpers.table_doc(fix_state=table.FIX_NOT_AFFECTED)
        doc["cves"][0]["distros"]["ubuntu-26.04"]["fixed_version"] = "0"
        f = assess.assess_cve(load(doc).get("CVE-2026-98432"), facts())
        self.assertEqual(f.verdict, assess.NOT_AFFECTED)
        self.assertFalse(f.in_range)


class TestExitCodes(unittest.TestCase):
    def test_fix_pending_exits_one(self):
        f = assess.assess_cve(load().get("CVE-2026-98432"), facts())
        self.assertEqual(assess.exit_code([f]), 1)

    def test_vulnerable_with_no_listeners_still_exits_one(self):
        # The card's rule: in range + no listener is still in range.
        f = assess.assess_cve(load().get("CVE-2026-98432"),
                              facts(mptcp_enabled=True, mptcp_listeners=()))
        self.assertIs(f.on_demonstrated_path, False)
        self.assertTrue(f.in_range)
        self.assertEqual(assess.exit_code([f]), 1)

    def test_unknown_exits_two(self):
        f = assess.assess_cve(load().get("CVE-2026-98432"), facts(distro="arch"))
        self.assertEqual(assess.exit_code([f]), 2)

    def test_clean_exits_zero(self):
        doc = helpers.table_doc(fix_state=table.FIX_RELEASED, fixed_version="7.0.0-38.38")
        f = assess.assess_cve(load(doc).get("CVE-2026-98432"),
                              facts(mptcp_enabled=False, mptcp_listeners=()))
        self.assertEqual(assess.exit_code([f]), 0)

    def test_finding_outranks_unmeasurable(self):
        pending = assess.assess_cve(load().get("CVE-2026-98432"), facts())
        unknown = assess.assess_cve(load().get("CVE-2026-98432"), facts(distro="arch"))
        self.assertEqual(assess.exit_code([unknown, pending]), 1)

    def test_patched_but_still_listening_exits_zero(self):
        # Documented decision: a patched host with MPTCP listeners is exit 0 with the
        # listener printed. Pinning 1 forever would get the gate switched off.
        doc = helpers.table_doc(fix_state=table.FIX_RELEASED, fixed_version="7.0.0-38.38")
        f = assess.assess_cve(load(doc).get("CVE-2026-98432"), facts())
        self.assertFalse(f.in_range)
        self.assertIs(f.on_demonstrated_path, True)
        self.assertEqual(assess.exit_code([f]), 0)

    def test_no_cves_measured_is_unmeasurable(self):
        self.assertEqual(assess.exit_code([]), 2)


if __name__ == "__main__":
    unittest.main()
