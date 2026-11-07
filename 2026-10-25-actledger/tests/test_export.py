import json
import os
import shutil
import tempfile
import unittest

from actledger.chain import GENESIS_HASH, make_entry
from actledger.export import (
    BINDINGS_ABSENT,
    BUNDLE_FORMAT,
    build_bundle,
    bundle_digest,
    read_bundle,
    verify_bundle,
    write_bundle,
)
from actledger.models import ActionRecord


def chain(n=3):
    entries, prev = [], GENESIS_HASH
    for i in range(n):
        record = ActionRecord(agent_id="forge", tool="file.read", outcome="ok-%d" % i)
        entry = make_entry(i, prev, record)
        entries.append(entry)
        prev = entry.hash
    return entries


class TestBuildBundle(unittest.TestCase):
    def test_bundle_declares_format_and_count(self):
        bundle = build_bundle(chain(), generated_at="2026-10-25T06:40:00Z")
        self.assertEqual(bundle["format"], BUNDLE_FORMAT)
        self.assertEqual(bundle["count"], 3)
        self.assertEqual(bundle["generated_at"], "2026-10-25T06:40:00Z")

    def test_bundle_head_is_the_last_entry_hash(self):
        entries = chain()
        self.assertEqual(build_bundle(entries)["head_hash"], entries[-1].hash)

    def test_bundle_carries_the_full_records(self):
        bundle = build_bundle(chain())
        self.assertEqual(bundle["entries"][0]["record"]["agent_id"], "forge")
        self.assertEqual(len(bundle["entries"]), 3)

    def test_empty_bundle_is_genesis(self):
        bundle = build_bundle([])
        self.assertEqual(bundle["count"], 0)
        self.assertEqual(bundle["head_hash"], GENESIS_HASH)

    def test_bundle_is_plain_json_serialisable(self):
        json.dumps(build_bundle(chain()))


class TestBundleDigest(unittest.TestCase):
    def test_digest_is_stable(self):
        bundle = build_bundle(chain(), generated_at="fixed")
        self.assertEqual(bundle_digest(bundle), bundle_digest(build_bundle(chain(), generated_at="fixed")))

    def test_digest_ignores_generated_at(self):
        a = build_bundle(chain(), generated_at="2026-10-25T00:00:00Z")
        b = build_bundle(chain(), generated_at="2026-10-26T00:00:00Z")
        self.assertEqual(bundle_digest(a), bundle_digest(b))

    def test_digest_changes_when_a_record_changes(self):
        bundle = build_bundle(chain())
        tampered = json.loads(json.dumps(bundle))
        tampered["entries"][1]["record"]["outcome"] = "FORGED"
        self.assertNotEqual(bundle_digest(bundle), bundle_digest(tampered))


class TestVerifyBundle(unittest.TestCase):
    def test_clean_chain_alone_is_not_checkable(self):
        # Chain-only bundle: the records are intact, but nothing in the artifact can
        # corroborate a digest or reproduce the posture. Not checkable != clean.
        result = verify_bundle(build_bundle(chain()))
        self.assertFalse(result.ok)
        self.assertEqual(result.state, BINDINGS_ABSENT)
        self.assertEqual(result.checked, 3)
        self.assertEqual(
            [brk.code for brk in result.breaks if brk.code != "BINDINGS-ABSENT"], []
        )

    def test_edited_record_fails_verification(self):
        bundle = json.loads(json.dumps(build_bundle(chain())))
        bundle["entries"][1]["record"]["outcome"] = "FORGED"
        result = verify_bundle(bundle)
        self.assertFalse(result.ok)
        self.assertIn("HASH-MISMATCH", [b.code for b in result.breaks])

    def test_dropped_tail_fails_verification(self):
        bundle = json.loads(json.dumps(build_bundle(chain())))
        bundle["entries"].pop()
        result = verify_bundle(bundle)
        self.assertFalse(result.ok)
        self.assertIn("COUNT-MISMATCH", [b.code for b in result.breaks])

    def test_wrong_format_is_rejected(self):
        bundle = build_bundle(chain())
        bundle["format"] = "something-else/1"
        result = verify_bundle(bundle)
        self.assertFalse(result.ok)
        self.assertIn("FORMAT-MISMATCH", [b.code for b in result.breaks])


class TestBundleFiles(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="actledger-export-")
        self.addCleanup(shutil.rmtree, self.dir, True)

    def test_write_and_read_round_trip(self):
        path = os.path.join(self.dir, "audit.bundle.json")
        bundle = build_bundle(chain())
        write_bundle(path, bundle)
        self.assertTrue(os.path.exists(path))
        self.assertEqual(read_bundle(path)["head_hash"], bundle["head_hash"])

    def test_written_bundle_round_trips_its_chain(self):
        path = os.path.join(self.dir, "audit.bundle.json")
        write_bundle(path, build_bundle(chain()))
        result = verify_bundle(read_bundle(path))
        self.assertEqual(result.checked, 3)
        self.assertEqual(
            [brk.code for brk in result.breaks if brk.code != "BINDINGS-ABSENT"], []
        )
        self.assertEqual(result.state, BINDINGS_ABSENT)

    def test_bundle_is_self_contained_no_ledger_paths(self):
        text = json.dumps(build_bundle(chain()))
        self.assertNotIn(".jsonl", text)
        self.assertNotIn("/home/", text)


if __name__ == "__main__":
    unittest.main()
