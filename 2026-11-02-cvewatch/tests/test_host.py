"""Host probing with injected inputs: no test may depend on the kernel of the machine running
it. The real host is exercised in the verification run, not in the unit suite."""

import os
import tempfile
import unittest
from collections import namedtuple

from cvewatch.host import facts, read_os_release, source_family

Completed = namedtuple("Completed", "returncode stdout stderr")


def runner_returning(stdout_text, code=0, stderr=""):
    # The payload parameter is 'stdout_text' so that it does not shadow the 'text' flag
    # subprocess.run accepts; shadowing it made the fake runner return a bool as stdout.
    def runner(args, capture_output=True, text=True, timeout=20):
        return Completed(code, stdout_text, stderr)
    return runner


OS_RELEASE = 'NAME="Ubuntu"\nVERSION_ID="26.04"\nVERSION_CODENAME=resolute\n'

DPKG = (
    "linux-image-7.0.0-38-generic\t7.0.0-38.38\tlinux\n"
    "linux-image-7.0.0-30-generic\t\tlinux\n"
    "linux-modules-7.0.0-38-generic\t7.0.0-38.38\tlinux\n"
    "linux-image-6.8.0-40-generic\t6.8.0-40.40\tlinux-hwe-6.8\n"
)


class OsReleaseTests(unittest.TestCase):
    def test_reads_version_and_codename(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "os-release")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(OS_RELEASE)
            values = read_os_release(path)
        self.assertEqual(values["VERSION_ID"], "26.04")
        self.assertEqual(values["VERSION_CODENAME"], "resolute")

    def test_missing_file_is_empty(self):
        self.assertEqual(read_os_release("/nonexistent/os-release"), {})


class SourceFamilyTests(unittest.TestCase):
    """Real dpkg on this host reports linux-image-7.0.0-38-generic's source as linux-signed.
    The tracker row is 'linux'. Without this mapping the running kernel is silently skipped."""

    def test_signed_maps_to_linux(self):
        self.assertEqual(source_family("linux-signed"), "linux")

    def test_meta_maps_to_linux(self):
        self.assertEqual(source_family("linux-meta"), "linux")

    def test_signed_hwe_keeps_flavour(self):
        self.assertEqual(source_family("linux-signed-hwe-6.8"), "linux-hwe-6.8")

    def test_meta_hwe_keeps_flavour(self):
        self.assertEqual(source_family("linux-meta-hwe-6.8"), "linux-hwe-6.8")

    def test_plain_source_unchanged(self):
        self.assertEqual(source_family("linux"), "linux")
        self.assertEqual(source_family("linux-hwe-6.8"), "linux-hwe-6.8")

    def test_empty_source(self):
        self.assertEqual(source_family(""), "")


class FactsTests(unittest.TestCase):
    def test_parses_kernels_and_skips_empty_versions(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "os-release")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(OS_RELEASE)
            collected = facts(os_release_path=path, runner=runner_returning(DPKG))
        self.assertEqual(collected.release_id, "26.04")
        self.assertEqual(collected.codename, "resolute")
        binaries = sorted(package.binary for package in collected.installed)
        self.assertEqual(binaries, ["linux-image-6.8.0-40-generic",
                                    "linux-image-7.0.0-38-generic"])
        self.assertEqual(collected.errors, ())

    def test_source_package_is_kept(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "os-release")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(OS_RELEASE)
            collected = facts(os_release_path=path, runner=runner_returning(DPKG))
        sources = {package.source for package in collected.installed}
        self.assertEqual(sources, {"linux", "linux-hwe-6.8"})

    def test_dpkg_failure_is_reported_not_swallowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "os-release")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(OS_RELEASE)
            collected = facts(os_release_path=path,
                              runner=runner_returning("", code=1, stderr="no dpkg"))
        self.assertEqual(collected.installed, ())
        self.assertTrue(collected.errors)
        self.assertIn("exited 1", collected.errors[0])

    def test_runner_exception_is_reported(self):
        def boom(*args, **kwargs):
            raise OSError("no such binary")
        collected = facts(os_release_path="/nonexistent/os-release", runner=boom)
        self.assertFalse(collected.measured)
        self.assertTrue(collected.errors)


if __name__ == "__main__":
    unittest.main()
