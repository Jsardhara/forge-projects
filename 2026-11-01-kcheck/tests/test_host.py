"""Parsers for the four local probes. Every one of them can fail, and a failure must
come back as ``None``/an error string -- never as a reassuring default.
"""

import unittest

import helpers
from kcheck import host


class TestDpkg(unittest.TestCase):
    def test_parses_real_transcript_including_blank_versions(self):
        pkgs = host.parse_dpkg(helpers.DPKG_REAL)
        self.assertEqual(pkgs["linux-image-7.0.0-38-generic"], "7.0.0-38.38")
        self.assertEqual(pkgs["linux-image-7.0.0-34-generic"], "7.0.0-34.34")
        # Two packages really do print an empty version; they must not become a package
        # called "linux-image-7.0.0-30-generic" with version "".
        self.assertIsNone(pkgs["linux-image-7.0.0-30-generic"])

    def test_tolerates_stderr_noise(self):
        text = "dpkg-query: warning: something\nlinux-image-7.0.0-38-generic 7.0.0-38.38\n"
        self.assertEqual(host.parse_dpkg(text)["linux-image-7.0.0-38-generic"], "7.0.0-38.38")

    def test_empty_output_is_an_empty_map_not_an_error(self):
        self.assertEqual(host.parse_dpkg(""), {})

    def test_package_for_release_finds_the_running_image(self):
        pkgs = host.parse_dpkg(helpers.DPKG_REAL)
        self.assertEqual(host.package_for_release(pkgs, "7.0.0-38-generic"),
                         ("linux-image-7.0.0-38-generic", "7.0.0-38.38"))

    def test_package_for_release_none_when_not_installed(self):
        pkgs = host.parse_dpkg(helpers.DPKG_REAL)
        self.assertIsNone(host.package_for_release(pkgs, "7.0.0-99-generic"))


class TestSysctl(unittest.TestCase):
    def test_reads_one(self):
        self.assertIs(host.parse_sysctl("net.mptcp.enabled = 1\n"), True)

    def test_reads_zero(self):
        self.assertIs(host.parse_sysctl("net.mptcp.enabled = 0\n"), False)

    def test_unreadable_is_none_not_false(self):
        # net.mptcp.enabled does not exist on kernels built without MPTCP. "Does not
        # apply" and "we could not look" are different claims; this returns None.
        self.assertIsNone(host.parse_sysctl(""))
        self.assertIsNone(host.parse_sysctl("sysctl: cannot stat /proc/sys/net/mptcp/enabled"))
        self.assertIsNone(host.parse_sysctl("net.mptcp.enabled = maybe"))


class TestSs(unittest.TestCase):
    def test_counts_real_listeners(self):
        listeners = host.parse_ss(helpers.SS_TAILNET)
        self.assertEqual(len(listeners), 5)
        self.assertEqual(listeners[0].port, "45480")

    def test_header_only_means_zero_listeners(self):
        self.assertEqual(len(host.parse_ss(helpers.SS_EMPTY)), 0)

    def test_parses_bracketed_ipv6(self):
        listeners = host.parse_ss(helpers.SS_TAILNET)
        v6 = [l for l in listeners if l.address.startswith("fd7a:")]
        self.assertEqual(len(v6), 2)
        self.assertEqual(v6[0].port, "443")

    def test_error_text_is_not_a_listener_count(self):
        # `ss -Mln` on a kernel without MPTCP diagnostics prints to stderr and exits 0
        # with just a header. Anything unparseable must be None so the caller says
        # "could not measure" instead of "zero listeners, nothing to see".
        self.assertIsNone(host.parse_ss("ss: unrecognized option 'M'"))


class TestExposureClassification(unittest.TestCase):
    CASES = (
        ("127.0.0.1", "localhost"),
        ("::1", "localhost"),
        ("100.107.170.75", "tailnet"),
        ("fd7a:115c:a1e0::c42d:aa4c", "tailnet"),
        ("192.168.0.41", "private_lan"),
        ("10.1.2.3", "private_lan"),
        ("172.20.0.9", "private_lan"),
        ("0.0.0.0", "all_interfaces"),
        ("::", "all_interfaces"),
        ("*", "all_interfaces"),
        ("203.0.113.9", "public"),
        ("8.8.8.8", "public"),
    )

    def test_classification_table(self):
        for address, expected in self.CASES:
            with self.subTest(address=address):
                self.assertEqual(host.classify_address(address)[0], expected)

    def test_classification_names_the_network_it_matched(self):
        # The repo uses 100.64.0.0/10, which is CGNAT, not Tailscale's own registry.
        # Say which range matched so a reader can disagree with the label.
        self.assertEqual(host.classify_address("100.107.170.75")[1], "100.64.0.0/10")
        self.assertEqual(host.classify_address("192.168.0.41")[1], "192.168.0.0/16")

    def test_surface_dedupes_and_orders_by_severity(self):
        listeners = host.parse_ss(helpers.SS_TAILNET + "LISTEN 0 4096 0.0.0.0:9999 0.0.0.0:*\n")
        surface = host.exposure_surface(listeners)
        self.assertEqual(surface, ("all_interfaces", "tailnet", "localhost"))

    def test_no_listeners_is_an_empty_surface(self):
        self.assertEqual(host.exposure_surface(()), ())


class TestGatherFromFixtures(unittest.TestCase):
    def test_full_fixture_set(self):
        facts = host.gather(fixtures=helpers.fixtures())
        self.assertEqual(facts.release, "7.0.0-38-generic")
        self.assertEqual(facts.package_version, "7.0.0-38.38")
        self.assertIs(facts.mptcp_enabled, True)
        self.assertEqual(len(facts.mptcp_listeners), 5)
        self.assertEqual(facts.exposure_surface, ("tailnet", "localhost"))
        self.assertEqual(facts.distro, "ubuntu")
        self.assertEqual(facts.distro_release, "26.04")
        self.assertEqual(facts.errors, ())

    def test_missing_probes_are_recorded_not_guessed(self):
        facts = host.gather(fixtures=helpers.fixtures(uname=None, dpkg=None, sysctl=None, ss=None))
        self.assertIsNone(facts.release)
        self.assertIsNone(facts.mptcp_enabled)
        self.assertIsNone(facts.mptcp_listeners)
        self.assertTrue(facts.errors)
        self.assertTrue(any("uname" in e for e in facts.errors))

    def test_missing_fixture_dir_reports_errors(self):
        facts = host.gather(fixtures="/nonexistent/kcheck-fixtures")
        self.assertIsNone(facts.release)
        self.assertTrue(facts.errors)


if __name__ == "__main__":
    unittest.main()
