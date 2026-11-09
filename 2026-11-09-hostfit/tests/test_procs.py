import os
import tempfile
import unittest

from hostfit.procs import read_processes, largest_covering

PID_DIRS = {
    "101": ("python", "VmRSS:\t19019492 kB\nName:\tpython\n"),
    "102": ("llama-server", "VmRSS:\t  5127352 kB\nName:\tllama-server\n"),
    "103": ("hermes", "VmRSS:\t  1264732 kB\nName:\thermes\n"),
}


def build_proc_tree(root):
    for pid, (comm, status) in PID_DIRS.items():
        d = os.path.join(root, pid)
        os.makedirs(d)
        with open(os.path.join(d, "comm"), "w") as fh:
            fh.write(comm + "\n")
        with open(os.path.join(d, "status"), "w") as fh:
            fh.write(status)


class ReadProcessesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        build_proc_tree(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_returns_rss_sorted_descending(self):
        scan = read_processes(self.tmp.name)
        self.assertEqual([p.comm for p in scan.procs], ["python", "llama-server", "hermes"])
        self.assertEqual(scan.procs[0].rss, 19019492 * 1024)
        self.assertEqual(scan.procs[0].pid, 101)

    def test_non_numeric_entries_are_skipped(self):
        os.makedirs(os.path.join(self.tmp.name, "self"))
        scan = read_processes(self.tmp.name)
        self.assertEqual(len(scan.procs), 3)

    def test_missing_procroot_is_unmeasured(self):
        scan = read_processes("/nonexistent/proc")
        self.assertIsNotNone(scan.unmeasured_reason)

    def test_process_vanishing_mid_read_is_counted_not_fatal(self):
        d = os.path.join(self.tmp.name, "202")
        os.makedirs(d)  # comm/status never written -> read race
        scan = read_processes(self.tmp.name)
        self.assertEqual(len(scan.procs), 3)
        self.assertEqual(scan.unreadable, 1)


class LargestCoveringTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        build_proc_tree(self.tmp.name)
        self.procs = read_processes(self.tmp.name).procs

    def tearDown(self):
        self.tmp.cleanup()

    def test_returns_smallest_prefix_that_covers_the_need(self):
        # python alone is 18.1 GiB; 20 GiB needs python plus the next holder.
        picked = largest_covering(self.procs, need=20 * 1024 ** 3)
        self.assertEqual([p.comm for p in picked], ["python", "llama-server"])

    def test_returns_empty_when_need_is_zero(self):
        self.assertEqual(largest_covering(self.procs, need=0), [])

    def test_gap_is_not_closable_when_every_process_is_not_enough(self):
        picked = largest_covering(self.procs, need=10 ** 15)
        self.assertIsNone(picked)


if __name__ == "__main__":
    unittest.main()
