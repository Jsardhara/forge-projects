import os
import tempfile
import unittest

import helpers
from skillbom.ledger import (
    capability_counts,
    diff_ledgers,
    divergence,
    ledger_from_json,
    ledger_to_json,
    skill_capability_counts,
    skill_counts,
)
from skillbom.scan import scan_roots

PY_NET = "import urllib.request\nurllib.request.urlopen('https://x')\n"
PY_EXEC = "import subprocess\nsubprocess.run(['ls'])\n"


class LedgerRoundTrip(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = self.tmp.name
        self.ledger = scan_roots([helpers.make_profile(self.base, "alpha", {
            "research/one": {"name": "one", "scripts": {"s/a.py": PY_NET}},
            "research/two": {"name": "two", "scripts": {"s/b.py": PY_EXEC}},
        })])

    def tearDown(self):
        self.tmp.cleanup()

    def test_json_round_trip_preserves_records(self):
        restored = ledger_from_json(ledger_to_json(self.ledger))
        self.assertEqual([s.rel for s in restored.skills], [s.rel for s in self.ledger.skills])
        for before, after in zip(self.ledger.skills, restored.skills):
            self.assertEqual(before.skill_md_sha256, after.skill_md_sha256)
            self.assertEqual([s.sha256 for s in before.scripts], [s.sha256 for s in after.scripts])
            self.assertEqual(before.declared_tools, after.declared_tools)

    def test_round_trip_preserves_capabilities(self):
        restored = ledger_from_json(ledger_to_json(self.ledger))
        self.assertEqual(
            [s.capabilities for s in restored.skills],
            [s.capabilities for s in self.ledger.skills],
        )

    def test_json_is_deterministic(self):
        self.assertEqual(ledger_to_json(self.ledger), ledger_to_json(self.ledger))


class Drift(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def _scan(self, skills, sub=""):
        base = os.path.join(self.base, sub) if sub else self.base
        return scan_roots([helpers.make_profile(base, "alpha", skills)])

    def test_no_change_is_empty_drift(self):
        a = self._scan({"one": {"name": "one"}})
        b = self._scan({"one": {"name": "one"}})
        drift = diff_ledgers(a, b)
        self.assertEqual((drift.added, drift.removed, drift.changed), ((), (), ()))
        self.assertFalse(drift)

    def test_added_skill(self):
        a = self._scan({"one": {"name": "one"}})
        b = self._scan({"one": {"name": "one"}, "two": {"name": "two"}})
        drift = diff_ledgers(a, b)
        self.assertEqual(drift.added, ("alpha:two",))
        self.assertTrue(drift)

    def test_removed_skill(self):
        a = self._scan({"one": {"name": "one"}, "two": {"name": "two"}}, sub="before")
        b = self._scan({"one": {"name": "one"}}, sub="after")
        self.assertEqual(diff_ledgers(a, b).removed, ("alpha:two",))

    def test_changed_script_content_is_drift(self):
        a = self._scan({"one": {"name": "one", "scripts": {"s/a.py": PY_NET}}})
        b = self._scan({"one": {"name": "one", "scripts": {"s/a.py": PY_NET + "# tweak\n"}}})
        drift = diff_ledgers(a, b)
        self.assertEqual(drift.changed, ("alpha:one",))
        self.assertEqual(drift.added, ())

    def test_changed_skill_md_is_drift(self):
        a = self._scan({"one": {"name": "one"}})
        b = self._scan({"one": {"name": "one", "description": "different text"}})
        self.assertEqual(diff_ledgers(a, b).changed, ("alpha:one",))

    def test_new_script_appearing_is_drift(self):
        a = self._scan({"one": {"name": "one"}})
        b = self._scan({"one": {"name": "one", "scripts": {"s/new.sh": "curl x\n"}}})
        self.assertEqual(diff_ledgers(a, b).changed, ("alpha:one",))


class Divergence(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def test_identical_copies_are_not_divergent(self):
        a = helpers.make_profile(self.base, "alpha", {"one": {"name": "one"}})
        b = helpers.make_profile(self.base, "beta", {"one": {"name": "one"}})
        self.assertEqual(divergence(scan_roots([a, b])), ())

    def test_different_content_under_one_name_diverges(self):
        a = helpers.make_profile(self.base, "alpha", {"one": {"name": "one"}})
        b = helpers.make_profile(self.base, "beta", {"one": {"name": "one", "description": "edited"}})
        found = divergence(scan_roots([a, b]))
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].name, "one")
        self.assertEqual(len(found[0].copies), 2)
        self.assertEqual(len({c.sha256 for c in found[0].copies}), 2)

    def test_single_copy_never_diverges(self):
        a = helpers.make_profile(self.base, "alpha", {"one": {"name": "one"}})
        self.assertEqual(divergence(scan_roots([a])), ())


class Counts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def test_distinct_skills_vs_copies(self):
        a = helpers.make_profile(self.base, "alpha", {"one": {"name": "one"}, "two": {"name": "two"}})
        b = helpers.make_profile(self.base, "beta", {"one": {"name": "one"}})
        ledger = scan_roots([a, b])
        skills, distinct = skill_counts(ledger)
        self.assertEqual(skills, 3)
        self.assertEqual(distinct, 2)

    def test_capability_counts_count_scripts(self):
        ledger = scan_roots([helpers.make_profile(self.base, "alpha", {
            "one": {"name": "one", "scripts": {"s/a.py": PY_NET, "s/b.py": PY_EXEC, "s/c.py": "x=1\n"}},
        })])
        counts = capability_counts(ledger)
        self.assertEqual(counts["network"], 1)
        self.assertEqual(counts["exec"], 1)
        self.assertEqual(counts.get("code_eval", 0), 0)

    def test_skill_capability_counts_count_skills(self):
        ledger = scan_roots([helpers.make_profile(self.base, "alpha", {
            "one": {"name": "one", "scripts": {"s/a.py": PY_NET, "s/b.py": PY_NET}},
            "two": {"name": "two", "scripts": {"s/c.py": "x=1\n"}},
        })])
        counts = skill_capability_counts(ledger)
        self.assertEqual(counts["network"], 1)


if __name__ == "__main__":
    unittest.main()
