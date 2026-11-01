import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout

import helpers
from skillbom.cli import main

NET = "import urllib.request\nurllib.request.urlopen('https://x')\n"


class CliContract(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = self.tmp.name
        self.root = helpers.make_profile(self.base, "alpha", {
            "research/one": {"name": "one", "scripts": {"s/a.py": NET}},
        })

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, argv):
        out = io.StringIO()
        with redirect_stdout(out):
            code = main(argv)
        return code, out.getvalue()

    def test_text_run_is_zero_and_mentions_the_profile(self):
        code, out = self._run(["--root", self.root.path])
        self.assertEqual(code, 0)
        self.assertIn("alpha", out)
        self.assertIn("1 skill", out)

    def test_json_run_is_parseable_and_complete(self):
        code, out = self._run(["--root", self.root.path, "--json"])
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(len(data["skills"]), 1)
        self.assertEqual(data["skills"][0]["name"], "one")
        self.assertEqual(data["skills"][0]["scripts"][0]["capabilities"], ["network"])

    def test_missing_root_exits_two(self):
        code, out = self._run(["--root", os.path.join(self.base, "ghost")])
        self.assertEqual(code, 2)
        self.assertIn("UNMEASURABLE", out.upper())

    def test_quiet_prints_nothing(self):
        code, out = self._run(["--root", self.root.path, "--quiet"])
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "")

    def test_ledger_out_then_diff_reports_drift(self):
        ledger_path = os.path.join(self.base, "ledger", "today.json")
        code, _ = self._run(["--root", self.root.path, "--ledger-out", ledger_path, "--quiet"])
        self.assertEqual(code, 0)
        self.assertTrue(os.path.exists(ledger_path))

        helpers.make_skill(self.root.path, "media/two", "two")
        code, out = self._run(["--root", self.root.path, "--diff", ledger_path])
        self.assertEqual(code, 1)
        self.assertIn("alpha:media/two", out)

    def test_diff_against_unchanged_ledger_is_zero(self):
        ledger_path = os.path.join(self.base, "l.json")
        self._run(["--root", self.root.path, "--ledger-out", ledger_path, "--quiet"])
        code, _ = self._run(["--root", self.root.path, "--diff", ledger_path, "--quiet"])
        self.assertEqual(code, 0)

    def test_diff_against_missing_ledger_is_unmeasurable(self):
        code, _ = self._run(["--root", self.root.path, "--diff", os.path.join(self.base, "nope.json")])
        self.assertEqual(code, 2)

    def test_diff_against_corrupt_ledger_is_unmeasurable(self):
        bad = helpers.write(os.path.join(self.base, "bad.json"), "{not json")
        code, _ = self._run(["--root", self.root.path, "--diff", bad])
        self.assertEqual(code, 2)

    def test_empty_root_is_unmeasurable_not_clean(self):
        empty = os.path.join(self.base, "empty")
        os.makedirs(empty)
        code, _ = self._run(["--root", empty])
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
