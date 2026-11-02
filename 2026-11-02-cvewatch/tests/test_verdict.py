"""The verdict layer: which row applies to this host, and what it means for the installed
version. The distinctions that matter are 'fix not built yet' vs 'fix shipped, you are
behind' vs 'already patched' - a tool that folds those together cannot drive a transition."""

import unittest

from cvewatch.tracker import CvePage, Row
from cvewatch.verdict import InstalledPackage, assess

HOST_38038 = [InstalledPackage(source="linux", binary="linux-image-7.0.0-38-generic",
                               version="7.0.0-38.38")]


def row(release_id="26.04", kind="vulnerable", fixed="7.0.0-43.43", released=False,
        package="linux", codename="resolute", qualifier="", detail=""):
    return Row(package, "%s LTS %s" % (release_id, codename), release_id, codename, qualifier,
               kind, fixed, released, detail or kind)


def page(*rows):
    return CvePage(cve_id="CVE-2026-98432", source="test", rows=tuple(rows))


class PendingFixTests(unittest.TestCase):
    def test_below_unreleased_target_is_pending_fix(self):
        result = assess(page(row()), "26.04", "resolute", HOST_38038)
        self.assertEqual(result.verdict, "VULNERABLE_PENDING_FIX")
        self.assertEqual(result.fixed_version, "7.0.0-43.43")

    def test_at_target_is_patched(self):
        installed = [InstalledPackage("linux", "linux-image-7.0.0-43-generic", "7.0.0-43.43")]
        result = assess(page(row()), "26.04", "resolute", installed)
        self.assertEqual(result.verdict, "PATCHED")

    def test_above_target_is_patched(self):
        installed = [InstalledPackage("linux", "linux-image-7.0.0-45-generic", "7.0.0-45.1")]
        self.assertEqual(assess(page(row()), "26.04", "resolute", installed).verdict, "PATCHED")

    def test_worst_binary_wins(self):
        installed = [
            InstalledPackage("linux", "linux-image-7.0.0-43-generic", "7.0.0-43.43"),
            InstalledPackage("linux", "linux-image-7.0.0-38-generic", "7.0.0-38.38"),
        ]
        result = assess(page(row()), "26.04", "resolute", installed)
        self.assertEqual(result.verdict, "VULNERABLE_PENDING_FIX")
        self.assertEqual([r.binary for r in result.rows if r.verdict.endswith("FIX")],
                         ["linux-image-7.0.0-38-generic"])


class FixReleasedTests(unittest.TestCase):
    def test_released_fix_below_is_actionable(self):
        result = assess(page(row(released=True)), "26.04", "resolute", HOST_38038)
        self.assertEqual(result.verdict, "VULNERABLE_FIX_AVAILABLE")

    def test_fix_available_outranks_pending_fix(self):
        installed = [
            InstalledPackage("linux", "linux-image-7.0.0-38-generic", "7.0.0-38.38"),
            InstalledPackage("linux", "linux-image-7.0.0-30-generic", "7.0.0-30.30"),
        ]
        rows = (row(package="linux"), row(package="linux", released=True, fixed="7.0.0-40.40"))
        self.assertEqual(assess(page(*rows), "26.04", "resolute", installed).verdict,
                         "VULNERABLE_FIX_AVAILABLE")


class NonVulnerableTests(unittest.TestCase):
    def test_plain_vulnerable_without_target(self):
        result = assess(page(row(fixed="")), "26.04", "resolute", HOST_38038)
        self.assertEqual(result.verdict, "VULNERABLE")

    def test_patched_row(self):
        result = assess(page(row(kind="patched", fixed="")), "26.04", "resolute", HOST_38038)
        self.assertEqual(result.verdict, "PATCHED")

    def test_ignored_row(self):
        result = assess(page(row(kind="ignored", fixed="", detail="Ignored end of life")),
                        "26.04", "resolute", HOST_38038)
        self.assertEqual(result.verdict, "IGNORED")

    def test_not_in_release_row(self):
        result = assess(page(row(kind="not_in_release", fixed="")), "26.04", "resolute",
                        HOST_38038)
        self.assertEqual(result.verdict, "NOT_IN_RELEASE")

    def test_pending_row(self):
        result = assess(page(row(kind="pending", fixed="")), "26.04", "resolute", HOST_38038)
        self.assertEqual(result.verdict, "VULNERABLE_PENDING_FIX")


class UnmeasurableTests(unittest.TestCase):
    def test_release_absent_from_page(self):
        result = assess(page(row(release_id="24.04")), "26.04", "resolute", HOST_38038)
        self.assertEqual(result.verdict, "UNKNOWN")
        self.assertIn("26.04", result.note)

    def test_no_installed_package_maps_to_row_source(self):
        installed = [InstalledPackage("linux-hwe", "linux-image-6.8.0-40-generic", "6.8.0-40.40")]
        result = assess(page(row()), "26.04", "resolute", installed)
        self.assertEqual(result.verdict, "UNKNOWN")

    def test_unknown_status_row_is_unknown(self):
        result = assess(page(row(kind="unknown", fixed="")), "26.04", "resolute", HOST_38038)
        self.assertEqual(result.verdict, "UNKNOWN")

    def test_ignored_does_not_mask_a_vulnerable_binary(self):
        installed = [
            InstalledPackage("linux", "linux-image-7.0.0-38-generic", "7.0.0-38.38"),
            InstalledPackage("linux-hwe", "linux-image-6.8.0-40-generic", "6.8.0-40.40"),
        ]
        rows = (row(package="linux", kind="ignored", fixed=""),
                row(package="linux-hwe", fixed="6.8.0-149.149"))
        self.assertEqual(assess(page(*rows), "26.04", "resolute", installed).verdict,
                         "VULNERABLE_PENDING_FIX")


if __name__ == "__main__":
    unittest.main()
