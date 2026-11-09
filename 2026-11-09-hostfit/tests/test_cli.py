import json
import os
import tempfile
import unittest
from unittest import mock

from hostfit import cli
from hostfit.meminfo import MemorySnapshot
from hostfit.procs import ProcInfo, ProcessScan

SNAP = MemorySnapshot(total=90 * 1024 ** 3, available=62 * 1024 ** 3, swap_free=8 * 1024 ** 3)
SCAN = ProcessScan(procs=[ProcInfo(pid=101, comm="python", rss=19 * 1024 ** 3)], unreadable=0)


class CliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def capture(self, argv, snap=SNAP, scan=SCAN):
        import io
        buf = io.StringIO()
        with mock.patch.object(cli, "snapshot_from_path", return_value=snap), \
             mock.patch.object(cli, "read_processes", return_value=scan), \
             mock.patch("sys.stdout", buf):
            code = cli.main(argv)
        return code, buf.getvalue()

    def test_peak_is_required_or_requirement_file(self):
        with self.assertRaises(SystemExit):
            self.capture([])

    def test_fit_exits_zero_and_prints_state(self):
        code, out = self.capture(["--peak-gib", "40"])
        self.assertEqual(code, 0)
        self.assertIn("FIT", out)

    def test_blocked_exits_one(self):
        code, _ = self.capture(["--peak-gib", "70"])
        self.assertEqual(code, 1)

    def test_unmeasured_meminfo_exits_two(self):
        bad = MemorySnapshot(total=None, available=None, swap_free=None,
                             unmeasured_reason="MemAvailable missing")
        code, out = self.capture(["--peak-gib", "1"], snap=bad)
        self.assertEqual(code, 2)
        self.assertIn("UNMEASURED", out)

    def test_json_output_is_parseable_and_carries_numbers(self):
        code, out = self.capture(["--peak-gib", "70", "--json"])
        payload = json.loads(out)
        self.assertEqual(code, 1)
        self.assertEqual(payload["state"], "BLOCKED_NOW")
        self.assertEqual(payload["requirement"]["name"], "cli")
        self.assertGreater(payload["reclaim_needed_gib"], 0)

    def test_requirement_file_is_read_and_named(self):
        path = os.path.join(self.tmp.name, "req.json")
        with open(path, "w") as fh:
            json.dump({"name": "dsv4-284b", "peak_gib": 57.61, "shm_gib": 0}, fh)
        code, out = self.capture(["--requirement", path])
        self.assertIn("dsv4-284b", out)

    def test_bad_requirement_file_exits_two_not_zero(self):
        path = os.path.join(self.tmp.name, "req.json")
        with open(path, "w") as fh:
            fh.write("{not json")
        code, _ = self.capture(["--requirement", path])
        self.assertEqual(code, 2)

    def test_top_consumers_are_listed_when_blocked(self):
        code, out = self.capture(["--peak-gib", "70", "--top", "3"])
        self.assertIn("python", out)


if __name__ == "__main__":
    unittest.main()
