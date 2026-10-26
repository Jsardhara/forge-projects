import unittest

from decoderattest.attest import Attestation, attest, severity_for
from decoderattest.inventory import NodeInstall, PythonInstall, SystemPackage
from decoderattest.rules import RuleSet
from decoderattest.vendored import VendoredCopy
from support import rule_doc


def rules():
    return RuleSet(rule_doc())


class SeverityTests(unittest.TestCase):
    def test_mapping_is_severity_dominant(self):
        self.assertEqual(severity_for("affected"), "CRITICAL")
        self.assertEqual(severity_for("unknown"), "WARN")
        self.assertEqual(severity_for("patched"), "OK")
        self.assertEqual(severity_for("not_affected"), "OK")


class AttestTests(unittest.TestCase):
    def test_exposed_node_drives_verdict(self):
        result = attest(
            rules(),
            nodes=[NodeInstall("/usr/bin/node", "26.8.2", None)],
            pythons=[],
            packages=[],
            vendored=[],
        )
        self.assertIsInstance(result, Attestation)
        self.assertEqual(result.verdict, "EXPOSED")
        self.assertEqual(result.findings[0].severity, "CRITICAL")
        self.assertEqual(result.findings[0].status, "affected")

    def test_clean_host_has_no_critical(self):
        result = attest(
            rules(),
            nodes=[NodeInstall("/usr/bin/node", "26.12.1", None)],
            pythons=[],
            packages=[],
            vendored=[],
        )
        self.assertEqual(result.verdict, "CLEAN")
        self.assertEqual(result.counts["found"], 1)

    def test_python_module_without_a_rule_is_not_reported_as_a_target(self):
        install = PythonInstall(
            "/usr/bin/python3",
            "3.14.7",
            {"zstandard": {"version": "0.22.0"}},
            None,
        )
        result = attest(rules(), [], [install], [], [])
        self.assertEqual(result.counts["found"], 0)

    def test_python_brotli_is_attested_independently_per_interpreter(self):
        good = PythonInstall("/a/python3", "3.11.9", {"Brotli": {"version": "1.2.1"}}, None)
        bad = PythonInstall("/b/python3", "3.12.4", {"Brotli": {"version": "1.2.0"}}, None)
        result = attest(rules(), [], [good, bad], [], [])
        statuses = {f.target: f.status for f in result.findings}
        self.assertEqual(statuses["/a/python3 :: Brotli"], "patched")
        self.assertEqual(statuses["/b/python3 :: Brotli"], "affected")

    def test_probe_failure_is_unknown_not_absent(self):
        install = PythonInstall("/a/python3", None, {}, "probe failed: boom")
        result = attest(rules(), [], [install], [], [])
        self.assertEqual(result.verdict, "UNKNOWN")
        self.assertEqual(result.findings[0].status, "unknown")

    def test_node_finding_carries_the_bundled_copy_note(self):
        result = attest(
            rules(), [NodeInstall("/usr/bin/node", "26.8.2", None)], [], [], []
        )
        self.assertIn("bundled", result.findings[0].note.lower())

    def test_vendored_affected_copy_is_critical(self):
        copy = VendoredCopy(
            header="/v/include/brotli/decode.h",
            version="1.2.0",
            has_block_switch=False,
            signals_agree=True,
            version_file="/v/common/version.h",
        )
        result = attest(rules(), [], [], [], [copy])
        self.assertEqual(result.findings[0].status, "affected")
        self.assertEqual(result.verdict, "EXPOSED")

    def test_vendored_version_spoofed_patched_is_unknown(self):
        copy = VendoredCopy(
            header="/v/include/brotli/decode.h",
            version="1.2.1",
            has_block_switch=False,
            signals_agree=False,
            version_file="/v/common/version.h",
        )
        result = attest(rules(), [], [], [], [copy])
        self.assertEqual(result.findings[0].status, "unknown")

    def test_vendored_without_version_but_with_marker_is_patched(self):
        copy = VendoredCopy(
            header="/v/include/brotli/decode.h",
            version=None,
            has_block_switch=True,
            signals_agree=True,
            version_file=None,
        )
        result = attest(rules(), [], [], [], [copy])
        self.assertEqual(result.findings[0].status, "patched")

    def test_vendored_with_neither_signal_is_affected(self):
        copy = VendoredCopy(
            header="/v/include/brotli/decode.h",
            version=None,
            has_block_switch=False,
            signals_agree=True,
            version_file=None,
        )
        result = attest(rules(), [], [], [], [copy])
        self.assertEqual(result.findings[0].status, "affected")
        self.assertIn("BLOCK_SWITCH", result.findings[0].reason)

    def test_findings_are_ordered_worst_first(self):
        result = attest(
            rules(),
            nodes=[NodeInstall("/usr/bin/node", "26.12.1", None)],
            pythons=[PythonInstall("/b/python3", "3.12.4", {"Brotli": {"version": "1.2.0"}}, None)],
            packages=[],
            vendored=[],
        )
        self.assertEqual([f.severity for f in result.findings], ["CRITICAL", "OK"])

    def test_counts_are_per_status(self):
        result = attest(
            rules(),
            nodes=[NodeInstall("/usr/bin/node", "26.8.2", None)],
            pythons=[PythonInstall("/p", "3.12.4", {"Brotli": {"version": "1.2.1"}}, None)],
            packages=[SystemPackage("libbrotli1", "1.2.0-3build1", "dpkg")],
            vendored=[],
        )
        self.assertEqual(result.counts["affected"], 2)
        self.assertEqual(result.counts["patched"], 1)
        self.assertEqual(result.counts["found"], 3)

    def test_python_interpreters_without_bindings_are_reported_as_probed(self):
        # An empty Python branch must not read as "Python is fine": say how many
        # interpreters were asked and how many had nothing importable.
        clean = PythonInstall("/usr/bin/python3", "3.14.7", {}, None)
        result = attest(rules(), [], [clean], [], [])
        joined = " ".join(result.notes)
        self.assertIn("1 python interpreter", joined)
        self.assertIn("0 with", joined)

    def test_python_interpreter_with_binding_is_not_double_reported(self):
        good = PythonInstall("/usr/bin/python3", "3.14.7", {"Brotli": {"version": "1.2.1"}}, None)
        result = attest(rules(), [], [good], [], [])
        self.assertNotIn("0 with", " ".join(result.notes))

    def test_a_host_with_nothing_found_is_not_a_pass(self):
        result = attest(rules(), [], [], [], [])
        self.assertEqual(result.verdict, "CLEAN")
        self.assertEqual(result.counts["found"], 0)
        self.assertTrue(result.notes and "no targets" in result.notes[0].lower())


if __name__ == "__main__":
    unittest.main()
