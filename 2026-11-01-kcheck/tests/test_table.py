"""The checked-in table is data, and data that lies silently is worse than no data.

These tests hold the line on two things:
  * every row carries its own provenance (source_url + retrieved_at), so a stale row is
    visible rather than silent;
  * a malformed or unknown table raises -- it never degrades into "looks patched".
"""

import json
import os
import unittest

import helpers
from kcheck import table as table_mod


class TestShippedTable(unittest.TestCase):
    """The real file, not a fixture: if the shipped data is wrong the tool is wrong."""

    @classmethod
    def setUpClass(cls):
        cls.doc = table_mod.load(helpers.SHIPPED_TABLE)

    def test_has_cve_2026_98432(self):
        self.assertIn("CVE-2026-98432", [c.cve for c in self.doc.cves])

    def test_every_distro_row_carries_provenance(self):
        for cve in self.doc.cves:
            self.assertTrue(cve.distros, "%s has no distro rows" % cve.cve)
            for key, row in cve.distros.items():
                with self.subTest(cve=cve.cve, distro=key):
                    self.assertTrue(row.source_url.startswith("https://"))
                    self.assertRegex(row.retrieved_at, r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")

    def test_ubuntu_2604_row_is_fix_pending_at_7_0_0_43_43(self):
        cve = self.doc.get("CVE-2026-98432")
        row = cve.distros["ubuntu-26.04"]
        self.assertEqual(row.fixed_version, "7.0.0-43.43")
        self.assertEqual(row.fix_state, table_mod.FIX_PENDING)
        self.assertIn("ubuntu.com/security", row.source_url)

    def test_cve_metadata_is_present_and_plausible(self):
        cve = self.doc.get("CVE-2026-98432")
        self.assertEqual(cve.cvss, 9.8)
        self.assertEqual(cve.vector, "AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H")
        self.assertTrue(cve.attack_path.label)
        # The mitigation is a pointer, never an automated action.
        self.assertFalse(cve.mitigation["automated"])

    def test_upstream_branches_parse(self):
        cve = self.doc.get("CVE-2026-98432")
        self.assertEqual(cve.branches["6.6"], "6.6.159")


class TestLoadValidation(unittest.TestCase):
    def _write(self, doc):
        path = os.path.join(helpers.tempdir(), "t.json")
        with open(path, "w") as fh:
            fh.write(doc if isinstance(doc, str) else json.dumps(doc))
        return path

    def test_missing_file_raises_with_the_path_named(self):
        missing = "/nonexistent/kcheck/fixed_versions.json"
        with self.assertRaises(table_mod.TableError) as ctx:
            table_mod.load(missing)
        self.assertIn(missing, str(ctx.exception))

    def test_bad_json_raises(self):
        with self.assertRaises(table_mod.TableError):
            table_mod.load(self._write("{not json"))

    def test_missing_source_url_is_rejected_at_load(self):
        doc = helpers.table_doc()
        del doc["cves"][0]["distros"]["ubuntu-26.04"]["source_url"]
        with self.assertRaises(table_mod.TableError) as ctx:
            table_mod.load(self._write(doc))
        self.assertIn("source_url", str(ctx.exception))

    def test_missing_retrieved_at_is_rejected_at_load(self):
        doc = helpers.table_doc()
        del doc["cves"][0]["distros"]["ubuntu-26.04"]["retrieved_at"]
        with self.assertRaises(table_mod.TableError):
            table_mod.load(self._write(doc))

    def test_unknown_fix_state_is_rejected_at_load(self):
        doc = helpers.table_doc()
        doc["cves"][0]["distros"]["ubuntu-26.04"]["fix_state"] = "probably-fine"
        with self.assertRaises(table_mod.TableError) as ctx:
            table_mod.load(self._write(doc))
        self.assertIn("fix_state", str(ctx.exception))

    def test_unparseable_fixed_version_is_rejected_at_load(self):
        doc = helpers.table_doc()
        doc["cves"][0]["distros"]["ubuntu-26.04"]["fixed_version"] = ""
        with self.assertRaises(table_mod.TableError):
            table_mod.load(self._write(doc))

    def test_missing_schema_version_is_rejected(self):
        doc = helpers.table_doc()
        del doc["schema_version"]
        with self.assertRaises(table_mod.TableError):
            table_mod.load(self._write(doc))


class TestLookup(unittest.TestCase):
    def test_distro_key_matches_os_release(self):
        doc = table_mod.load(helpers.SHIPPED_TABLE)
        self.assertEqual(table_mod.distro_key("ubuntu", "26.04"), "ubuntu-26.04")
        self.assertIsNotNone(doc.for_distro("CVE-2026-98432", "ubuntu-26.04"))

    def test_unknown_distro_returns_none_not_a_guess(self):
        doc = table_mod.load(helpers.SHIPPED_TABLE)
        self.assertIsNone(doc.for_distro("CVE-2026-98432", "arch"))
        self.assertIsNone(doc.for_distro("CVE-2026-98432", "ubuntu-24.04"))

    def test_unknown_cve_returns_none(self):
        doc = table_mod.load(helpers.SHIPPED_TABLE)
        self.assertIsNone(doc.get("CVE-1999-0001"))


class TestStaleness(unittest.TestCase):
    def test_fresh_row_is_not_stale(self):
        doc = table_mod.load(helpers.SHIPPED_TABLE)
        row = doc.get("CVE-2026-98432").distros["ubuntu-26.04"]
        age = table_mod.age_days(row.retrieved_at, now="2026-11-01T07:00:00Z")
        self.assertEqual(age, 0)
        self.assertFalse(table_mod.is_stale(age, doc.stale_after_days))

    def test_old_row_is_stale(self):
        age = table_mod.age_days("2026-10-01T00:00:00Z", now="2026-11-01T07:00:00Z")
        self.assertEqual(age, 31)
        self.assertTrue(table_mod.is_stale(age, 7))

    def test_unparseable_timestamp_is_stale_not_fresh(self):
        # Unknown age must fail toward "look at this", never toward "fine".
        age = table_mod.age_days("last tuesday", now="2026-11-01T07:00:00Z")
        self.assertIsNone(age)
        self.assertTrue(table_mod.is_stale(age, 7))


if __name__ == "__main__":
    unittest.main()
