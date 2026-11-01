import os
import tempfile
import unittest

import helpers
from skillbom.models import Root
from skillbom.scan import scan_roots


class ScanDiscovery(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def test_finds_every_skill_in_every_root(self):
        a = helpers.make_profile(self.base, "alpha", {
            "research/one": {"name": "one", "scripts": {"scripts/run.py": "print(1)\n"}},
            "media/two": {"name": "two"},
        })
        b = helpers.make_profile(self.base, "beta", {
            "research/one": {"name": "one"},
        })
        ledger = scan_roots([a, b])
        self.assertEqual(len(ledger.skills), 3)
        self.assertEqual({s.root for s in ledger.skills}, {"alpha", "beta"})
        self.assertEqual(ledger.unreadable, ())

    def test_records_relative_path_not_absolute_prefix_noise(self):
        a = helpers.make_profile(self.base, "alpha", {"research/one": {"name": "one"}})
        ledger = scan_roots([a])
        self.assertEqual(ledger.skills[0].rel, "research/one")

    def test_script_hashes_and_sizes(self):
        a = helpers.make_profile(self.base, "alpha", {
            "one": {"name": "one", "scripts": {"scripts/run.sh": "curl https://x\n"}},
        })
        ledger = scan_roots([a])
        script = ledger.skills[0].scripts[0]
        expected = helpers.sha256_file(os.path.join(a.path, "one", "scripts", "run.sh"))
        self.assertEqual(script.sha256, expected)
        self.assertEqual(script.size, len("curl https://x\n"))
        self.assertEqual(script.rel, "scripts/run.sh")

    def test_non_script_files_are_not_scripts(self):
        a = helpers.make_profile(self.base, "alpha", {
            "one": {"name": "one", "scripts": {"references/doc.md": "text\n", "data.json": "{}\n"}},
        })
        ledger = scan_roots([a])
        self.assertEqual(ledger.skills[0].scripts, ())

    def test_underscore_and_dot_dirs_are_excluded_and_counted(self):
        a = helpers.make_profile(self.base, "alpha", {"one": {"name": "one"}})
        helpers.make_skill(os.path.join(a.path, "_trash"), "old", "old")
        helpers.make_skill(os.path.join(a.path, ".archive"), "older", "older")
        ledger = scan_roots([a])
        self.assertEqual(len(ledger.skills), 1)
        self.assertEqual(len(ledger.excluded), 2)
        self.assertTrue(any("_trash" in e for e in ledger.excluded))

    def test_skills_are_sorted_deterministically(self):
        a = helpers.make_profile(self.base, "alpha", {
            "b/zed": {"name": "zed"}, "a/alpha": {"name": "alpha"},
        })
        ledger = scan_roots([a])
        self.assertEqual([s.rel for s in ledger.skills], ["a/alpha", "b/zed"])

    def test_declared_tools_and_frontmatter_flag(self):
        a = helpers.make_profile(self.base, "alpha", {
            "one": {"name": "one", "tools": ["Read", "Bash"]},
        })
        ledger = scan_roots([a])
        self.assertEqual(ledger.skills[0].declared_tools, ("Read", "Bash"))
        self.assertTrue(ledger.skills[0].frontmatter_ok)

    def test_skill_name_falls_back_to_directory_when_frontmatter_broken(self):
        a = helpers.make_profile(self.base, "alpha", {"research/one": {"name": "one"}})
        helpers.write(os.path.join(a.path, "research", "one", "SKILL.md"), "# no frontmatter\n")
        ledger = scan_roots([a])
        self.assertEqual(ledger.skills[0].name, "one")
        self.assertFalse(ledger.skills[0].frontmatter_ok)
        self.assertEqual(ledger.skills[0].problem, "no-frontmatter")


class ScanMeasurability(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def test_missing_root_is_unmeasurable_not_empty(self):
        missing = Root(label="ghost", path=os.path.join(self.base, "nope"), kind="profile")
        ledger = scan_roots([missing])
        self.assertEqual(ledger.skills, ())
        self.assertEqual(len(ledger.unreadable), 1)
        self.assertIn("ghost", ledger.unreadable[0])

    def test_root_that_is_a_file_is_unmeasurable(self):
        path = helpers.write(os.path.join(self.base, "file.txt"), "x")
        ledger = scan_roots([Root(label="f", path=path, kind="profile")])
        self.assertEqual(len(ledger.unreadable), 1)

    def test_unreadable_script_is_reported_and_hashing_continues(self):
        a = helpers.make_profile(self.base, "alpha", {
            "one": {"name": "one", "scripts": {"scripts/a.py": "print(1)\n", "scripts/b.py": "print(2)\n"}},
        })
        os.chmod(os.path.join(a.path, "one", "scripts", "b.py"), 0o000)
        try:
            ledger = scan_roots([a])
        finally:
            os.chmod(os.path.join(a.path, "one", "scripts", "b.py"), 0o644)
        if os.geteuid() == 0:
            self.skipTest("root can read 0000 files; unreadable path not reachable")
        self.assertEqual(len(ledger.skills[0].scripts), 1)
        self.assertTrue(any("b.py" in u for u in ledger.unreadable))


if __name__ == "__main__":
    unittest.main()
