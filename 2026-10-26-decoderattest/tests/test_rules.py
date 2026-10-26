import json
import os
import unittest

from decoderattest.rules import RuleSet, RuleError
from support import TmpTree, rule_doc, write


class LoadTests(unittest.TestCase):
    def test_loads_from_path(self):
        with TmpTree() as root:
            path = write(os.path.join(root, "rules.json"), json.dumps(rule_doc()))
            rules = RuleSet.load(path)
        self.assertEqual(rules.advisory["id"], "CVE-2099-0001")
        self.assertEqual(len(rules.products), 3)

    def test_missing_file_is_loud(self):
        with self.assertRaises(RuleError):
            RuleSet.load("/nonexistent/rules.json")

    def test_bad_json_is_loud(self):
        with TmpTree() as root:
            path = write(os.path.join(root, "rules.json"), "{not json")
            with self.assertRaises(RuleError):
                RuleSet.load(path)

    def test_product_without_kind_is_rejected(self):
        doc = rule_doc()
        del doc["products"][0]["kind"]
        with TmpTree() as root:
            path = write(os.path.join(root, "rules.json"), json.dumps(doc))
            with self.assertRaises(RuleError):
                RuleSet.load(path)

    def test_unknown_kind_is_rejected(self):
        doc = rule_doc()
        doc["products"][0]["kind"] = "magic"
        with TmpTree() as root:
            path = write(os.path.join(root, "rules.json"), json.dumps(doc))
            with self.assertRaises(RuleError):
                RuleSet.load(path)


class RangeEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.rules = RuleSet(rule_doc())

    def status(self, ecosystem, package, version):
        return self.rules.evaluate(ecosystem, package, version).status

    def test_inside_span_is_affected(self):
        self.assertEqual(self.status("python", "Brotli", "1.2.0"), "affected")

    def test_below_span_is_not_affected(self):
        self.assertEqual(self.status("python", "Brotli", "1.0.2"), "not_affected")

    def test_above_span_is_not_affected(self):
        self.assertEqual(self.status("python", "Brotli", "1.3.0"), "not_affected")

    def test_fixed_version_inside_span_is_patched(self):
        # 1.1.1 sits numerically inside 1.0.3..1.2.0 but is a published fix
        self.assertEqual(self.status("python", "Brotli", "1.1.1"), "patched")

    def test_package_name_match_is_case_insensitive(self):
        self.assertEqual(self.status("python", "brotli", "1.2.0"), "affected")

    def test_unknown_package_is_not_listed(self):
        self.assertEqual(self.status("python", "zstandard", "0.22.0"), "not_listed")

    def test_debian_revision_is_ignored(self):
        self.assertEqual(self.status("system", "libbrotli1", "1.2.0-3build1"), "affected")

    def test_max_exclusive_boundary(self):
        self.assertEqual(self.status("system", "libbrotli1", "1.2.1"), "patched")

    def test_unparsable_version_is_unknown_not_a_guess(self):
        self.assertEqual(self.status("python", "Brotli", "weird"), "unknown")


class RuntimeLineTests(unittest.TestCase):
    def setUp(self):
        self.rules = RuleSet(rule_doc())

    def status(self, version):
        return self.rules.evaluate("node", "node", version).status

    def test_below_line_fix_is_affected(self):
        self.assertEqual(self.status("26.8.2"), "affected")

    def test_at_line_fix_is_patched(self):
        self.assertEqual(self.status("26.12.1"), "patched")

    def test_above_line_fix_is_patched(self):
        self.assertEqual(self.status("26.12.2"), "patched")

    def test_eol_line_is_affected_whatever_the_version(self):
        self.assertEqual(self.status("25.99.0"), "affected")
        self.assertEqual(self.status("20.11.1"), "affected")

    def test_unlisted_newer_line_is_unknown(self):
        # a major newer than any listed line cannot be attested from this rule
        self.assertEqual(self.status("27.0.0"), "unknown")


class ShippedRuleFileTests(unittest.TestCase):
    """The rule file that ships must reproduce the published advisory table."""

    def setUp(self):
        from decoderattest.rules import default_rules_path

        self.rules = RuleSet.load(default_rules_path())

    def test_node_versions(self):
        cases = {
            "26.8.2": "affected",
            "26.12.1": "patched",
            "24.22.0": "affected",
            "24.22.1": "patched",
            "22.23.3": "affected",
            "22.23.4": "patched",
            "25.1.0": "affected",
            "18.20.0": "affected",
        }
        for version, expected in cases.items():
            self.assertEqual(
                self.rules.evaluate("node", "node", version).status,
                expected,
                msg="node %s" % version,
            )

    def test_python_brotli_versions(self):
        cases = {
            "1.0.3": "affected",
            "1.2.0": "affected",
            "1.0.10": "patched",
            "1.1.1": "patched",
            "1.2.1": "patched",
            "1.0.2": "not_affected",
            "1.3.0": "not_affected",
        }
        for version, expected in cases.items():
            self.assertEqual(
                self.rules.evaluate("python", "Brotli", version).status,
                expected,
                msg="Brotli %s" % version,
            )

    def test_brotlicffi_versions(self):
        cases = {"1.2.0.9": "affected", "1.2.1.0": "patched", "1.0.2.0": "not_affected"}
        for version, expected in cases.items():
            self.assertEqual(
                self.rules.evaluate("python", "brotlicffi", version).status,
                expected,
                msg="brotlicffi %s" % version,
            )

    def test_system_library_versions(self):
        cases = {
            "1.2.0-3build1": "affected",
            "1.0.9": "affected",
            "1.1.0": "affected",
            "1.0.10": "patched",
            "1.1.1": "patched",
            "1.2.1": "patched",
            "1.0.2": "not_affected",
        }
        for version, expected in cases.items():
            self.assertEqual(
                self.rules.evaluate("system", "libbrotli1", version).status,
                expected,
                msg="libbrotli1 %s" % version,
            )

    def test_advisory_is_the_real_one(self):
        self.assertEqual(self.rules.advisory["id"], "CVE-2026-111497")
        self.assertIn("GHSA-9v8h-qqgm-4m35", self.rules.advisory["aliases"])


if __name__ == "__main__":
    unittest.main()
