"""Discovery: find verifier projects in a repo root by path convention.

Membership is *registered* (see specs.DEFAULT_SPECS) because the repo also holds
non-verifier projects that ship a `cli.py`; running those as if they were
verifiers produces noise, which is what posture exists to remove.
"""

import os
import tempfile
import unittest

from posture.discover import DEFAULT_SPECS, discover, project_name


def make_verifier(root, dirname, module, cli=True, main=True):
    d = os.path.join(root, dirname)
    src = os.path.join(d, "src", module)
    os.makedirs(src, exist_ok=True)
    if cli:
        with open(os.path.join(src, "cli.py"), "w") as fh:
            fh.write("# fake\n")
    if main:
        with open(os.path.join(src, "__main__.py"), "w") as fh:
            fh.write("# fake\n")
    with open(os.path.join(d, "README.md"), "w") as fh:
        fh.write("# fake\n")
    return d


class ProjectNameTest(unittest.TestCase):
    def test_strips_date_prefix(self):
        self.assertEqual(project_name("2026-11-02-cvewatch"), "cvewatch")

    def test_keeps_dashes_in_name(self):
        self.assertEqual(project_name("2026-01-01-foo-bar"), "foo-bar")

    def test_rejects_non_dated(self):
        self.assertIsNone(project_name("INDEX.md"))
        self.assertIsNone(project_name("some-dir"))

    def test_rejects_undated_lookalike(self):
        self.assertIsNone(project_name("2026-1-1-short"))

    def test_rejects_impossible_date(self):
        self.assertIsNone(project_name("2026-02-30-foo"))


class DiscoverTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def test_finds_registered_verifier_by_convention(self):
        make_verifier(self.root, "2026-01-01-kcheck", "kcheck")
        found = discover(self.root)
        self.assertEqual([f.spec.name for f in found], ["kcheck"])

    def test_ignores_unregistered_project_by_default(self):
        make_verifier(self.root, "2026-01-01-randomtool", "randomtool")
        self.assertEqual(discover(self.root), [])

    def test_include_unknown_opts_in(self):
        make_verifier(self.root, "2026-01-01-randomtool", "randomtool")
        found = discover(self.root, include_unknown=True)
        self.assertEqual([f.spec.name for f in found], ["randomtool"])
        self.assertFalse(found[0].spec.known)

    def test_unknown_verifier_gets_no_default_args(self):
        make_verifier(self.root, "2026-01-01-randomtool", "randomtool")
        found = discover(self.root, include_unknown=True)
        self.assertEqual(found[0].spec.args, ())

    def test_known_verifier_carries_registered_args(self):
        for name in DEFAULT_SPECS:
            make_verifier(self.root, "2026-01-01-" + name, name)
        found = {f.spec.name: f.spec for f in discover(self.root)}
        self.assertTrue(found["cvewatch"].known)
        self.assertIn("--cve", found["cvewatch"].args)
        self.assertEqual(len(found), len(DEFAULT_SPECS))

    def test_ignores_project_without_cli(self):
        make_verifier(self.root, "2026-01-01-kcheck", "kcheck", cli=False)
        self.assertEqual(discover(self.root), [])

    def test_ignores_non_dated_dir(self):
        make_verifier(self.root, "kcheck", "kcheck")
        self.assertEqual(discover(self.root), [])

    def test_sorted_by_name_is_deterministic(self):
        make_verifier(self.root, "2026-01-02-skillbom", "skillbom")
        make_verifier(self.root, "2026-01-01-kcheck", "kcheck")
        self.assertEqual([f.spec.name for f in discover(self.root)], ["kcheck", "skillbom"])

    def test_names_are_unique_even_with_two_dated_dirs(self):
        make_verifier(self.root, "2026-01-01-kcheck", "kcheck")
        make_verifier(self.root, "2026-02-01-kcheck", "kcheck")
        found = discover(self.root)
        self.assertEqual(len(found), 1)

    def test_module_name_comes_from_package_dir(self):
        d = os.path.join(self.root, "2026-01-01-kcheck")
        pkg = os.path.join(d, "src", "kcheck_pkg")
        os.makedirs(pkg)
        open(os.path.join(pkg, "cli.py"), "w").close()
        open(os.path.join(pkg, "__main__.py"), "w").close()
        found = discover(self.root)
        self.assertEqual(found[0].spec.module, "kcheck_pkg")

    def test_only_filter(self):
        make_verifier(self.root, "2026-01-01-kcheck", "kcheck")
        make_verifier(self.root, "2026-01-02-exitpath", "exitpath")
        found = discover(self.root, only=["exitpath"])
        self.assertEqual([f.spec.name for f in found], ["exitpath"])

    def test_only_unknown_name_returns_empty(self):
        make_verifier(self.root, "2026-01-01-kcheck", "kcheck")
        self.assertEqual(discover(self.root, only=["nope"]), [])

    def test_excluded_name_is_never_returned(self):
        make_verifier(self.root, "2026-01-01-kcheck", "kcheck")
        self.assertEqual(discover(self.root, exclude=["kcheck"]), [])

    def test_missing_root_raises(self):
        with self.assertRaises(OSError):
            discover(os.path.join(self.root, "does-not-exist"))


if __name__ == "__main__":
    unittest.main()
