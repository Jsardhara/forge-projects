"""State: atomic save, never-crash load, and signal normalisation."""

import os
import tempfile
import unittest

from posture.models import CLEAN, FINDINGS, UNMEASURABLE, VerifierResult
from posture.state import (
    SCHEMA,
    load_state,
    normalize_signal,
    save_state,
    signal_digest,
    diff_results,
)


def result(name, status, digest="d1", exit_code=0):
    return VerifierResult(
        name=name, status=status, exit_code=exit_code, duration_s=0.1,
        digest=digest, error=None,
    )


class NormalizeTest(unittest.TestCase):
    def test_iso_timestamp_is_removed(self):
        a = "posture 2026-11-03T06:20:28Z clean"
        b = "posture 2026-11-04T07:00:00Z clean"
        self.assertEqual(normalize_signal(a), normalize_signal(b))

    def test_extra_pattern_is_stripped(self):
        """A counter is not a verdict: block heights must not flap the digest."""
        pattern = (r"block \d+",)
        self.assertEqual(
            normalize_signal("ethereum healthy block 26332507", extra=pattern),
            normalize_signal("ethereum healthy block 53449152", extra=pattern),
        )

    def test_extra_pattern_changes_nothing_when_absent(self):
        self.assertEqual(
            normalize_signal("kraken degraded", extra=(r"block \d+",)),
            normalize_signal("kraken degraded"),
        )

    def test_invalid_extra_pattern_does_not_raise(self):
        self.assertEqual(
            normalize_signal("x", extra=("([unclosed",)), normalize_signal("x")
        )

    def test_duration_is_removed(self):
        self.assertEqual(
            normalize_signal("ran 12 tests in 0.544s"),
            normalize_signal("ran 12 tests in 1.902s"),
        )

    def test_real_content_difference_survives(self):
        self.assertNotEqual(
            normalize_signal("VULNERABLE_PENDING_FIX"),
            normalize_signal("PATCHED"),
        )

    def test_trailing_whitespace_is_ignored(self):
        self.assertEqual(normalize_signal("a\n\nb  \n"), normalize_signal("a\nb"))

    def test_digest_is_stable_across_runs_with_timestamps(self):
        self.assertEqual(
            signal_digest("x 2026-11-03T06:20:28Z"),
            signal_digest("x 2026-11-05T09:11:02Z"),
        )


class SaveLoadTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "sub", "state.json")

    def tearDown(self):
        self.tmp.cleanup()

    def test_missing_state_loads_none(self):
        self.assertIsNone(load_state(self.path))

    def test_round_trip(self):
        rows = {"alpha": result("alpha", CLEAN)}
        save_state(self.path, rows, now="2026-11-03T06:00:00Z")
        state = load_state(self.path)
        self.assertEqual(state["schema"], SCHEMA)
        self.assertEqual(state["generated_at"], "2026-11-03T06:00:00Z")
        self.assertEqual(state["rows"]["alpha"]["status"], CLEAN)

    def test_creates_parent_dirs(self):
        save_state(self.path, {"alpha": result("alpha", CLEAN)})
        self.assertTrue(os.path.exists(self.path))

    def test_corrupt_state_loads_none_not_raise(self):
        os.makedirs(os.path.dirname(self.path))
        with open(self.path, "w") as fh:
            fh.write("{not json")
        self.assertIsNone(load_state(self.path))

    def test_wrong_schema_loads_none(self):
        os.makedirs(os.path.dirname(self.path))
        with open(self.path, "w") as fh:
            fh.write('{"schema": 99, "rows": {}}')
        self.assertIsNone(load_state(self.path))

    def test_save_is_atomic_leaves_no_tmp(self):
        save_state(self.path, {"alpha": result("alpha", CLEAN)})
        self.assertEqual(os.listdir(os.path.dirname(self.path)), ["state.json"])


class DiffTest(unittest.TestCase):
    def test_first_run_has_no_transitions(self):
        current = {"alpha": result("alpha", CLEAN)}
        self.assertEqual(diff_results(None, current), [])

    def test_status_change_is_a_transition(self):
        previous = {"rows": {"alpha": result("alpha", CLEAN).to_dict()}}
        current = {"alpha": result("alpha", FINDINGS, "d2", 1)}
        transitions = diff_results(previous, current)
        self.assertEqual(len(transitions), 1)
        self.assertEqual(transitions[0].field, "status")
        self.assertEqual(transitions[0].before, CLEAN)
        self.assertEqual(transitions[0].after, FINDINGS)

    def test_new_verifier_is_a_transition(self):
        previous = {"rows": {}}
        current = {"alpha": result("alpha", CLEAN)}
        transitions = diff_results(previous, current)
        self.assertEqual(transitions[0].field, "appeared")

    def test_vanished_verifier_is_a_transition(self):
        previous = {"rows": {"alpha": result("alpha", CLEAN).to_dict()}}
        transitions = diff_results(previous, {})
        self.assertEqual(transitions[0].field, "vanished")

    def test_digest_change_alone_is_a_transition(self):
        previous = {"rows": {"alpha": result("alpha", CLEAN, "old").to_dict()}}
        current = {"alpha": result("alpha", CLEAN, "new")}
        transitions = diff_results(previous, current)
        self.assertEqual([t.field for t in transitions], ["signal"])

    def test_identical_run_is_silent(self):
        previous = {"rows": {"alpha": result("alpha", CLEAN).to_dict()}}
        current = {"alpha": result("alpha", CLEAN)}
        self.assertEqual(diff_results(previous, current), [])

    def test_transition_carries_names(self):
        previous = {"rows": {"alpha": result("alpha", CLEAN).to_dict()}}
        current = {"alpha": result("alpha", UNMEASURABLE, "d", None)}
        self.assertEqual(diff_results(previous, current)[0].name, "alpha")


if __name__ == "__main__":
    unittest.main()
