import unittest

from actledger.chain import (
    GENESIS_HASH,
    canonical_json,
    entry_hash,
    make_entry,
    sha256_hex,
    verify_entries,
    verify_lines,
)
from actledger.models import ActionRecord


def rec(agent="forge", tool="file.write", outcome="ok", **kw):
    return ActionRecord(agent_id=agent, tool=tool, outcome=outcome, **kw)


class TestCanonicalJson(unittest.TestCase):
    def test_sorts_keys_and_strips_whitespace(self):
        self.assertEqual(canonical_json({"b": 1, "a": 2}), '{"a":2,"b":1}')

    def test_is_ascii_safe(self):
        self.assertNotIn("\u00e9", canonical_json({"k": "caf\u00e9"}))

    def test_nested_structures_are_stable(self):
        left = canonical_json({"x": [3, {"b": 1, "a": 2}]})
        right = canonical_json({"x": [3, {"a": 2, "b": 1}]})
        self.assertEqual(left, right)


class TestHashing(unittest.TestCase):
    def test_sha256_hex_is_64_lowercase_hex(self):
        digest = sha256_hex("abc")
        self.assertEqual(len(digest), 64)
        self.assertEqual(digest, digest.lower())
        self.assertTrue(all(c in "0123456789abcdef" for c in digest))

    def test_sha256_hex_known_vector(self):
        self.assertEqual(
            sha256_hex("abc"),
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
        )

    def test_genesis_hash_is_64_zeros(self):
        self.assertEqual(GENESIS_HASH, "0" * 64)

    def test_entry_hash_is_deterministic(self):
        a = entry_hash(0, GENESIS_HASH, rec().to_dict())
        b = entry_hash(0, GENESIS_HASH, rec().to_dict())
        self.assertEqual(a, b)

    def test_entry_hash_binds_seq_prev_and_record(self):
        base = entry_hash(0, GENESIS_HASH, rec().to_dict())
        self.assertNotEqual(base, entry_hash(1, GENESIS_HASH, rec().to_dict()))
        self.assertNotEqual(base, entry_hash(0, "f" * 64, rec().to_dict()))
        self.assertNotEqual(base, entry_hash(0, GENESIS_HASH, rec(outcome="denied").to_dict()))


class TestMakeEntry(unittest.TestCase):
    def test_first_entry_links_to_genesis(self):
        entry = make_entry(0, GENESIS_HASH, rec())
        self.assertEqual(entry.seq, 0)
        self.assertEqual(entry.prev_hash, GENESIS_HASH)
        self.assertEqual(entry.hash, entry_hash(0, GENESIS_HASH, rec().to_dict()))

    def test_entry_to_dict_round_trips_record(self):
        entry = make_entry(2, "a" * 64, rec(data_touched=("a.txt",)))
        payload = entry.to_dict()
        self.assertEqual(payload["seq"], 2)
        self.assertEqual(payload["record"]["data_touched"], ["a.txt"])


class TestVerifyEntries(unittest.TestCase):
    def _chain(self, n=3):
        entries, prev = [], GENESIS_HASH
        for i in range(n):
            entry = make_entry(i, prev, rec(outcome="ok-%d" % i))
            entries.append(entry)
            prev = entry.hash
        return entries

    def test_clean_chain_verifies(self):
        entries = self._chain()
        result = verify_entries(entries, expected_head=entries[-1].hash)
        self.assertTrue(result.ok, result.breaks)
        self.assertEqual(result.checked, 3)
        self.assertEqual(result.head_hash, entries[-1].hash)

    def test_empty_chain_is_ok_at_genesis(self):
        result = verify_entries([], expected_head=GENESIS_HASH)
        self.assertTrue(result.ok)
        self.assertEqual(result.checked, 0)
        self.assertEqual(result.head_hash, GENESIS_HASH)

    def test_edited_record_is_caught(self):
        entries = self._chain()
        target = entries[1]
        forged = make_entry(1, target.prev_hash, rec(outcome="FORGED"))
        forged = forged.__class__(
            seq=target.seq,
            record=rec(outcome="FORGED"),
            prev_hash=target.prev_hash,
            hash=target.hash,  # keep the old hash: the lie is the point
        )
        entries[1] = forged
        result = verify_entries(entries)
        self.assertFalse(result.ok)
        self.assertIn("HASH-MISMATCH", [b.code for b in result.breaks])
        self.assertEqual(result.breaks[0].seq, 1)

    def test_reordered_records_are_caught(self):
        entries = self._chain()
        entries[1], entries[2] = entries[2], entries[1]
        result = verify_entries(entries)
        self.assertFalse(result.ok)
        self.assertTrue(
            {"SEQ-GAP", "PREV-MISMATCH", "HASH-MISMATCH"} & {b.code for b in result.breaks}
        )

    def test_deleted_middle_record_is_caught(self):
        entries = self._chain()
        del entries[1]
        result = verify_entries(entries)
        self.assertFalse(result.ok)
        codes = {b.code for b in result.breaks}
        self.assertIn("SEQ-GAP", codes)
        self.assertIn("PREV-MISMATCH", codes)

    def test_truncated_chain_is_caught_against_committed_head(self):
        entries = self._chain()
        committed = entries[-1].hash
        result = verify_entries(entries[:-1], expected_head=committed)
        self.assertFalse(result.ok)
        self.assertIn("HEAD-MISMATCH", [b.code for b in result.breaks])

    def test_every_break_carries_seq_and_detail(self):
        entries = self._chain()
        result = verify_entries(entries[:-1], expected_head=entries[-1].hash)
        for brk in result.breaks:
            self.assertTrue(brk.code)
            self.assertTrue(brk.detail)


class TestVerifyLines(unittest.TestCase):
    def test_lines_round_trip(self):
        entry = make_entry(0, GENESIS_HASH, rec())
        result = verify_lines([entry.to_json_line()], expected_head=entry.hash)
        self.assertTrue(result.ok)
        self.assertEqual(result.checked, 1)

    def test_malformed_line_is_a_break_not_a_crash(self):
        result = verify_lines(["{not json"], expected_head=None)
        self.assertFalse(result.ok)
        self.assertEqual(result.breaks[0].code, "PARSE-ERROR")

    def test_blank_lines_are_ignored(self):
        entry = make_entry(0, GENESIS_HASH, rec())
        result = verify_lines(["\n", entry.to_json_line(), "  \n"], expected_head=entry.hash)
        self.assertTrue(result.ok, result.breaks)
        self.assertEqual(result.checked, 1)


if __name__ == "__main__":
    unittest.main()
