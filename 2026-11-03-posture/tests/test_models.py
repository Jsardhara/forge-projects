"""Models: exit-code classification and the immutable result record."""

import unittest

from posture.models import (
    CLEAN,
    ERROR,
    FINDINGS,
    UNMEASURABLE,
    VerifierResult,
    status_for_exit,
)


class StatusForExitTest(unittest.TestCase):
    def test_zero_is_clean(self):
        self.assertEqual(status_for_exit(0), CLEAN)

    def test_one_is_findings(self):
        self.assertEqual(status_for_exit(1), FINDINGS)

    def test_two_is_unmeasurable(self):
        self.assertEqual(status_for_exit(2), UNMEASURABLE)

    def test_other_codes_are_error_not_clean(self):
        for code in (3, 127, -9):
            self.assertEqual(status_for_exit(code), ERROR)

    def test_none_is_error(self):
        self.assertEqual(status_for_exit(None), ERROR)


class VerifierResultTest(unittest.TestCase):
    def test_needs_human_for_findings_and_unmeasurable(self):
        res = VerifierResult(
            name="alpha", status=FINDINGS, exit_code=1, duration_s=0.1,
            digest="d", error=None,
        )
        self.assertTrue(res.needs_human)
        # A finding is still a measurement: the tool answered, it just did not like
        # the answer. `measured` means "we got a trustworthy answer", not "clean".
        self.assertTrue(res.measured)

    def test_clean_is_measured_and_needs_nobody(self):
        res = VerifierResult(
            name="alpha", status=CLEAN, exit_code=0, duration_s=0.1,
            digest="d", error=None,
        )
        self.assertFalse(res.needs_human)
        self.assertTrue(res.measured)

    def test_error_is_not_measured(self):
        res = VerifierResult(
            name="alpha", status=ERROR, exit_code=None, duration_s=0.1,
            digest="d", error="timeout",
        )
        self.assertFalse(res.measured)
        self.assertTrue(res.needs_human)

    def test_result_is_frozen(self):
        res = VerifierResult(
            name="alpha", status=CLEAN, exit_code=0, duration_s=0.1,
            digest="d", error=None,
        )
        with self.assertRaises(Exception):
            res.status = FINDINGS

    def test_round_trip_to_dict(self):
        res = VerifierResult(
            name="alpha", status=FINDINGS, exit_code=1, duration_s=0.25,
            digest="abc", error=None,
        )
        again = VerifierResult.from_dict(res.to_dict())
        self.assertEqual(again, res)


if __name__ == "__main__":
    unittest.main()
