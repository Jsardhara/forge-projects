import tempfile
import unittest

import helpers
from skillbom.ledger import diff_ledgers
from skillbom.models import Root
from skillbom.report import exit_code, render_text
from skillbom.scan import scan_roots

NET = "import urllib.request\nurllib.request.urlopen('https://x')\n"


class TextReport(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = self.tmp.name
        self.ledger = scan_roots([helpers.make_profile(self.base, "alpha", {
            "research/one": {"name": "one", "scripts": {"s/a.py": NET}, "tools": ["Read"]},
            "media/two": {"name": "two"},
        })])

    def tearDown(self):
        self.tmp.cleanup()

    def test_names_the_profile_and_counts(self):
        text = render_text(self.ledger)
        self.assertIn("alpha", text)
        self.assertIn("2 skills", text)

    def test_lists_capabilities_present(self):
        text = render_text(self.ledger)
        self.assertIn("network", text)

    def test_top_section_shows_the_highest_authority_skill(self):
        text = render_text(self.ledger, top=5)
        self.assertIn("one", text.split("--top")[-1] if "--top" in text else text)
        self.assertIn("TOP", text.upper())

    def test_top_zero_disables_the_section(self):
        text = render_text(self.ledger, top=0)
        self.assertNotIn("TOP AUTHORITY", text.upper())

    def test_unmeasurable_is_printed_loudly(self):
        ledger = scan_roots([Root(label="ghost", path="/nonexistent/x", kind="profile")])
        text = render_text(ledger)
        self.assertIn("UNMEASURABLE", text.upper())
        self.assertIn("ghost", text)

    def test_drift_section(self):
        later = scan_roots([helpers.make_profile(self.base, "alpha", {
            "research/one": {"name": "one", "scripts": {"s/a.py": NET}, "tools": ["Read"]},
            "media/three": {"name": "three"},
        })])
        drift = diff_ledgers(self.ledger, later)
        text = render_text(later, drift=drift)
        self.assertIn("DRIFT", text.upper())
        self.assertIn("alpha:media/three", text)

    def test_text_is_pure_ascii(self):
        render_text(self.ledger).encode("ascii")


class ExitCodes(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def test_clean_is_zero(self):
        ledger = scan_roots([helpers.make_profile(self.base, "alpha", {"one": {"name": "one"}})])
        self.assertEqual(exit_code(ledger), 0)

    def test_divergence_is_one(self):
        a = helpers.make_profile(self.base, "alpha", {"one": {"name": "one"}})
        b = helpers.make_profile(self.base, "beta", {"one": {"name": "one", "description": "x"}})
        self.assertEqual(exit_code(scan_roots([a, b])), 1)

    def test_unmeasurable_is_two_and_beats_a_finding(self):
        a = helpers.make_profile(self.base, "alpha", {"one": {"name": "one"}})
        b = helpers.make_profile(self.base, "beta", {"one": {"name": "one", "description": "x"}})
        ghost = Root(label="ghost", path="/nonexistent/x", kind="profile")
        self.assertEqual(exit_code(scan_roots([a, b, ghost])), 2)

    def test_drift_is_one(self):
        a = scan_roots([helpers.make_profile(self.base, "alpha", {"one": {"name": "one"}})])
        b = scan_roots([helpers.make_profile(self.base, "alpha", {
            "one": {"name": "one"}, "two": {"name": "two"}})])
        self.assertEqual(exit_code(b, drift=diff_ledgers(a, b)), 1)


if __name__ == "__main__":
    unittest.main()
