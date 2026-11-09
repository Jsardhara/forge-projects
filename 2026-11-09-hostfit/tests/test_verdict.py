import unittest

from hostfit.meminfo import MemorySnapshot
from hostfit.verdict import Requirement, evaluate, GIB

TOTAL = 90 * GIB
AVAIL = 62 * GIB


def snap(available=AVAIL, total=TOTAL, reason=None):
    return MemorySnapshot(
        total=total,
        available=available,
        swap_free=8 * GIB,
        unmeasured_reason=reason,
    )


def req(peak_gib, shm_gib=0.0, headroom_pct=10.0):
    return Requirement(
        name="probe",
        peak_bytes=int(peak_gib * GIB),
        shm_bytes=int(shm_gib * GIB),
        headroom_pct=headroom_pct,
    )


class StateTest(unittest.TestCase):
    def test_unmeasured_snapshot_is_never_a_pass(self):
        v = evaluate(snap(reason="MemAvailable missing"), req(1))
        self.assertEqual(v.state, "UNMEASURED")

    def test_peak_above_physical_total_is_impossible(self):
        v = evaluate(snap(), req(200))
        self.assertEqual(v.state, "IMPOSSIBLE")

    def test_comfortable_margin_is_fit(self):
        v = evaluate(snap(), req(40))  # 62 - 40 = 22 GiB margin
        self.assertEqual(v.state, "FIT")
        self.assertEqual(v.exit_code, 0)

    def test_margin_inside_headroom_is_tight(self):
        v = evaluate(snap(), req(58))  # 4 GiB margin < 5.8 GiB headroom
        self.assertEqual(v.state, "TIGHT")
        self.assertEqual(v.exit_code, 1)

    def test_negative_margin_is_blocked_now_with_reclaim_number(self):
        v = evaluate(snap(), req(70))  # 8 GiB short of what is available today
        self.assertEqual(v.state, "BLOCKED_NOW")
        self.assertEqual(v.reclaim_needed, 8 * GIB)
        self.assertEqual(v.exit_code, 1)

    def test_swap_is_never_counted_as_capacity(self):
        # 62 GiB available, 1 GiB short; 8 GiB swap free must not rescue it.
        v = evaluate(snap(), req(63))
        self.assertEqual(v.state, "BLOCKED_NOW")

    def test_headroom_is_configurable_and_zero_headroom_makes_exact_margin_fit(self):
        v = evaluate(snap(), req(62, headroom_pct=0))
        self.assertEqual(v.state, "FIT")

    def test_shm_shortfall_blocks_even_when_ram_is_plenty(self):
        v = evaluate(snap(), req(10, shm_gib=64), shm_available=45 * GIB)
        self.assertEqual(v.state, "BLOCKED_NOW")
        self.assertTrue(any("shm" in r for r in v.reasons))


class ReportingTest(unittest.TestCase):
    def test_reasons_always_name_the_numbers_used(self):
        v = evaluate(snap(), req(58))
        joined = " ".join(v.reasons)
        self.assertIn("62.0 GiB available", joined)
        self.assertIn("58.0 GiB required", joined)

    def test_shm_is_only_checked_when_the_requirement_asks_for_it(self):
        v = evaluate(snap(), req(10), shm_available=None)
        self.assertEqual(v.state, "FIT")
        self.assertFalse(any("shm" in r for r in v.reasons))


if __name__ == "__main__":
    unittest.main()
