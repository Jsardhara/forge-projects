"""State file + transitions. The only thing allowed to alert is a change, so the diff has to
be precise: a repeated 'still vulnerable' run must produce zero transitions."""

import json
import os
import tempfile
import unittest

from cvewatch.state import diff, load, save, snapshot


def entry(verdict="VULNERABLE_PENDING_FIX", fixed="7.0.0-43.43", installed=None,
          release="26.04"):
    return snapshot(verdict=verdict, fixed_version=fixed, release=release,
                    installed=installed or [["linux-image-7.0.0-38-generic", "7.0.0-38.38"]])


class RoundTripTests(unittest.TestCase):
    def test_save_then_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "state.json")
            doc = {"CVE-2026-98432": entry()}
            save(path, doc)
            self.assertEqual(load(path), doc)

    def test_save_is_atomic_and_creates_dirs(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "nested", "dir", "state.json")
            save(path, {"CVE-1": entry()})
            self.assertTrue(os.path.exists(path))
            with open(path, encoding="utf-8") as handle:
                json.load(handle)

    def test_missing_state_loads_empty(self):
        self.assertEqual(load("/nonexistent/path/state.json"), {})

    def test_corrupt_state_loads_empty_not_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "state.json")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("{not json")
            self.assertEqual(load(path), {})


class DiffTests(unittest.TestCase):
    def test_no_change_is_no_transition(self):
        doc = {"CVE-1": entry()}
        self.assertEqual(diff(doc, {"CVE-1": entry()}), [])

    def test_new_cve(self):
        found = diff({}, {"CVE-1": entry()})
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].kind, "new_cve")

    def test_fix_released_transition(self):
        found = diff({"CVE-1": entry(verdict="VULNERABLE_PENDING_FIX")},
                     {"CVE-1": entry(verdict="PATCHED", fixed="7.0.0-43.43")})
        self.assertEqual([t.kind for t in found], ["verdict_changed"])
        self.assertEqual(found[0].before, "VULNERABLE_PENDING_FIX")
        self.assertEqual(found[0].after, "PATCHED")

    def test_target_version_changed(self):
        found = diff({"CVE-1": entry(fixed="7.0.0-43.43")},
                     {"CVE-1": entry(fixed="7.0.0-44.44")})
        self.assertEqual([t.kind for t in found], ["target_version_changed"])

    def test_kernel_changed_under_unchanged_verdict(self):
        found = diff(
            {"CVE-1": entry(installed=[["linux-image-7.0.0-38-generic", "7.0.0-38.38"]])},
            {"CVE-1": entry(installed=[["linux-image-7.0.0-40-generic", "7.0.0-40.40"]])})
        self.assertEqual([t.kind for t in found], ["kernel_changed"])

    def test_cve_dropped_from_watch_list_is_not_an_alert(self):
        self.assertEqual(diff({"CVE-1": entry()}, {}), [])

    def test_multiple_changes_reported_individually(self):
        found = diff({"CVE-1": entry(fixed="7.0.0-43.43")},
                     {"CVE-1": entry(fixed="7.0.0-44.44", verdict="PATCHED"),
                      "CVE-2": entry()})
        kinds = sorted(t.kind for t in found)
        self.assertEqual(kinds, ["new_cve", "target_version_changed", "verdict_changed"])

    def test_transition_renders_one_line(self):
        found = diff({"CVE-1": entry()}, {"CVE-1": entry(verdict="PATCHED")})
        text = found[0].render()
        self.assertIn("CVE-1", text)
        self.assertIn("VULNERABLE_PENDING_FIX", text)
        self.assertIn("PATCHED", text)


if __name__ == "__main__":
    unittest.main()
