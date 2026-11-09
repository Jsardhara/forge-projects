import unittest

from hostfit.meminfo import parse_meminfo, snapshot_from_text, snapshot_from_path

SAMPLE = """MemTotal:       94067788 kB
MemFree:         1657568 kB
MemAvailable:   65885332 kB
Buffers:         2060232 kB
Cached:         61755752 kB
SwapTotal:       8388604 kB
SwapFree:        8373168 kB
Dirty:              5512 kB
SReclaimable:    2057784 kB
CommitLimit:    55422496 kB
Committed_AS:   32599044 kB
HugePages_Total:       0
"""


class ParseMeminfoTest(unittest.TestCase):
    def test_parses_kb_lines_into_bytes(self):
        values = parse_meminfo(SAMPLE)
        self.assertEqual(values["MemTotal"], 94067788 * 1024)
        self.assertEqual(values["MemAvailable"], 65885332 * 1024)

    def test_skips_lines_without_a_colon(self):
        values = parse_meminfo("garbage line\nMemTotal: 1024 kB\n")
        self.assertEqual(set(values), {"MemTotal"})

    def test_missing_units_are_not_parsed_as_bytes(self):
        # A line with no kB unit is not a byte count we can trust.
        values = parse_meminfo("MemTotal: 94067788\n")
        self.assertNotIn("MemTotal", values)


class SnapshotTest(unittest.TestCase):
    def test_snapshot_carries_total_available_swap(self):
        snap = snapshot_from_text(SAMPLE)
        self.assertIsNone(snap.unmeasured_reason)
        self.assertEqual(snap.total, 94067788 * 1024)
        self.assertEqual(snap.available, 65885332 * 1024)
        self.assertEqual(snap.swap_free, 8373168 * 1024)

    def test_missing_memavailable_is_unmeasured_not_zero(self):
        snap = snapshot_from_text("MemTotal: 1024 kB\n")
        self.assertIsNotNone(snap.unmeasured_reason)
        self.assertIn("MemAvailable", snap.unmeasured_reason)
        self.assertIsNone(snap.available)

    def test_missing_file_is_unmeasured(self):
        snap = snapshot_from_path("/nonexistent/meminfo")
        self.assertIsNotNone(snap.unmeasured_reason)

    def test_swap_is_reported_but_never_added_to_available(self):
        snap = snapshot_from_text(SAMPLE)
        self.assertNotEqual(snap.available, snap.available + snap.swap_free)


if __name__ == "__main__":
    unittest.main()
