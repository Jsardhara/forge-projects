import os
import shutil
import tempfile
import unittest

from actledger.chain import GENESIS_HASH
from actledger.ledger import Ledger, LedgerError
from actledger.models import ActionRecord


def rec(outcome="ok", **kw):
    return ActionRecord(agent_id="forge", tool="file.write", outcome=outcome, **kw)


class LedgerTestCase(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="actledger-")
        self.path = os.path.join(self.dir, "actions.jsonl")
        self.addCleanup(shutil.rmtree, self.dir, True)


class TestAppend(LedgerTestCase):
    def test_first_append_links_to_genesis(self):
        ledger = Ledger(self.path)
        entry = ledger.append(rec())
        self.assertEqual(entry.seq, 0)
        self.assertEqual(entry.prev_hash, GENESIS_HASH)
        self.assertTrue(os.path.exists(self.path))

    def test_appends_are_chained(self):
        ledger = Ledger(self.path)
        first = ledger.append(rec("one"))
        second = ledger.append(rec("two"))
        third = ledger.append(rec("three"))
        self.assertEqual(second.prev_hash, first.hash)
        self.assertEqual(third.prev_hash, second.hash)
        self.assertEqual([e.seq for e in ledger.entries()], [0, 1, 2])

    def test_head_sidecar_is_written(self):
        ledger = Ledger(self.path)
        ledger.append(rec())
        count, head = Ledger(self.path).head()
        self.assertEqual(count, 1)
        self.assertEqual(len(head), 64)

    def test_file_is_one_json_object_per_line(self):
        ledger = Ledger(self.path)
        ledger.append(rec())
        ledger.append(rec())
        with open(self.path, "r", encoding="utf-8") as handle:
            lines = [line for line in handle.read().splitlines() if line.strip()]
        self.assertEqual(len(lines), 2)
        self.assertTrue(all(line.startswith("{") and line.endswith("}") for line in lines))

    def test_reopen_continues_the_chain(self):
        Ledger(self.path).append(rec("a"))
        reopened = Ledger(self.path)
        entry = reopened.append(rec("b"))
        self.assertEqual(entry.seq, 1)
        self.assertTrue(reopened.verify().ok)

    def test_missing_parent_directory_fails_loudly(self):
        ledger = Ledger(os.path.join(self.dir, "nope", "actions.jsonl"))
        with self.assertRaises(LedgerError):
            ledger.append(rec())

    def test_record_round_trips_through_disk(self):
        record = rec(data_touched=("a.txt",), verifier="sentinel", args_hash="ab" * 32)
        Ledger(self.path).append(record)
        loaded = Ledger(self.path).entries()[0].record
        self.assertEqual(loaded, record)


class TestDriftDetection(LedgerTestCase):
    def test_append_refuses_when_a_line_was_deleted(self):
        ledger = Ledger(self.path)
        ledger.append(rec("a"))
        ledger.append(rec("b"))
        with open(self.path, "r", encoding="utf-8") as handle:
            lines = handle.read().splitlines()
        with open(self.path, "w", encoding="utf-8") as handle:
            handle.write(lines[0] + "\n")
        with self.assertRaises(LedgerError):
            Ledger(self.path).append(rec("c"))

    def test_append_refuses_when_a_line_was_appended_behind_its_back(self):
        ledger = Ledger(self.path)
        ledger.append(rec("a"))
        with open(self.path, "a", encoding="utf-8") as handle:
            handle.write('{"seq":1,"record":{},"prev_hash":"x","hash":"y"}\n')
        with self.assertRaises(LedgerError):
            Ledger(self.path).append(rec("b"))

    def test_verify_reports_tampering(self):
        ledger = Ledger(self.path)
        ledger.append(rec("a"))
        ledger.append(rec("b"))
        with open(self.path, "r", encoding="utf-8") as handle:
            text = handle.read()
        with open(self.path, "w", encoding="utf-8") as handle:
            handle.write(text.replace('"outcome":"a"', '"outcome":"A"'))
        result = Ledger(self.path).verify()
        self.assertFalse(result.ok)
        self.assertTrue(result.breaks)

    def test_verify_uses_the_committed_head_to_catch_truncation(self):
        ledger = Ledger(self.path)
        for i in range(3):
            ledger.append(rec("r%d" % i))
        with open(self.path, "r", encoding="utf-8") as handle:
            lines = handle.read().splitlines()
        with open(self.path, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines[:2]) + "\n")
        result = Ledger(self.path).verify()
        self.assertFalse(result.ok)
        self.assertIn("HEAD-MISMATCH", [b.code for b in result.breaks])

    def test_clean_ledger_verifies(self):
        ledger = Ledger(self.path)
        for i in range(4):
            ledger.append(rec("r%d" % i))
        result = ledger.verify()
        self.assertTrue(result.ok)
        self.assertEqual(result.checked, 4)


if __name__ == "__main__":
    unittest.main()
