"""The bundle must let a receiver on another machine falsify what it claims.

Before this change `build_bundle` carried five keys and no bindings, so every `ws1:`
digest inside a bundle was a transcription that looked exactly like evidence, and the
declared posture was a claim the artifact could not recompute. These tests pin the two
legs the project exists to carry — responsibility and provenance — to the artifact
itself, and pin the honest third state for a bundle that carries neither: not checkable,
never clean.
"""

import io
import json
import os
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout

from actledger import cli
from actledger.export import (
    BINDINGS_ABSENT,
    BUNDLE_FORMAT,
    BUNDLE_FORMAT_V1,
    MISMATCH,
    PASS,
    UNMEASURABLE,
    build_bundle,
    bundle_digest,
    verify_bundle,
    write_bundle,
    read_bundle,
)
from actledger.ledger import Ledger
from actledger.manifest import (
    DerivedDigest,
    append_binding,
    load_binding_records,
)
from actledger.models import ActionRecord

DIGEST = "b" * 64
FINGERPRINT = "a" * 64


def _record(index, tagged=True, verifier="sentinel", approved=True):
    return ActionRecord(
        agent_id="forge",
        tool="file.read",
        outcome="ok-%d" % index,
        ts="2026-11-07T06:00:0%dZ" % index,
        model_id="wan2.2-vae" if tagged else "",
        model_digest=("ws1:" + DIGEST) if tagged else "",
        policy_version="pol-1",
        verifier=verifier,
        approved_by="jyot" if approved else "",
        approved_at="2026-11-07T05:00:00Z" if approved else "",
    )


class _LedgerCase(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="actledger-bundle-")
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.path = os.path.join(self.dir, "actions.jsonl")

    def ledger(self, n=2, tagged=True, verifier="sentinel", bind=True):
        ledger = Ledger(self.path)
        for index in range(n):
            ledger.append(_record(index, tagged=tagged, verifier=verifier))
        if bind and tagged:
            derived = DerivedDigest(
                digest=DIGEST,
                tagged="ws1:" + DIGEST,
                tensor_count=196,
                format="safetensors",
                manifest_sha256=FINGERPRINT,
            )
            for seq in range(n):
                append_binding(
                    self.path, seq, derived, "/home/jyot/models/wan2.2_vae.manifest.json",
                    "2026-11-07T06:00:00Z",
                )
        return Ledger(self.path).entries()

    def bundle(self, **kwargs):
        entries = self.ledger(**kwargs)
        return build_bundle(entries, load_binding_records(self.path))


class TestBundleCarriesTheProof(_LedgerCase):
    def test_bundle_declares_v2(self):
        self.assertEqual(self.bundle()["format"], BUNDLE_FORMAT)

    def test_bundle_carries_one_binding_per_measured_row(self):
        bundle = self.bundle()
        self.assertEqual(len(bundle["bindings"]), 2)
        self.assertEqual(bundle["bindings"][0]["model_digest"], "ws1:" + DIGEST)
        self.assertEqual(bundle["bindings"][0]["tensor_count"], 196)

    def test_binding_travels_the_fingerprint_and_the_basename(self):
        binding = self.bundle()["bindings"][0]
        self.assertEqual(binding["manifest_sha256"], FINGERPRINT)
        self.assertEqual(binding["manifest_basename"], "wan2.2_vae.manifest.json")

    def test_binding_does_not_travel_the_exporting_machine_abspath(self):
        text = json.dumps(self.bundle())
        self.assertNotIn("/home/", text)
        self.assertNotIn(".jsonl", text)

    def test_bundle_carries_the_declared_posture(self):
        declared = self.bundle()["audit"]
        self.assertEqual(declared["total"], 2)
        self.assertEqual(declared["severity"], "PASS")

    def test_declared_posture_is_the_recomputed_one(self):
        # A ledger with no named verifier must be exported with that verdict, not a nicer one.
        bundle = self.bundle(verifier="")
        self.assertEqual(bundle["audit"]["severity"], "FLAG")
        self.assertEqual(bundle["audit"]["unverified"], 2)

    def test_digest_covers_the_bindings(self):
        bundle = self.bundle()
        tampered = json.loads(json.dumps(bundle))
        tampered["bindings"][0]["tensor_count"] = 1
        self.assertNotEqual(bundle_digest(bundle), bundle_digest(tampered))


class TestVerifyBundleProvesIt(_LedgerCase):
    def test_a_bundle_with_matching_bindings_is_clean(self):
        result = verify_bundle(self.bundle())
        self.assertTrue(result.ok, result.breaks)
        self.assertEqual(result.state, PASS)
        self.assertEqual(result.checked, 2)

    def test_each_measured_row_is_reported_as_corroborated(self):
        result = verify_bundle(self.bundle())
        self.assertEqual([check.state for check in result.bindings], [PASS, PASS])

    def test_a_binding_edited_inside_the_bundle_is_a_mismatch(self):
        # The forgery case: bindings are outside the hash chain, so the bundle is the
        # only place this can be caught.
        bundle = self.bundle()
        bundle["bindings"][1]["model_digest"] = "ws1:" + ("c" * 64)
        result = verify_bundle(bundle)
        self.assertFalse(result.ok)
        self.assertEqual(result.state, MISMATCH)
        self.assertIn("BINDING-MISMATCH", [brk.code for brk in result.breaks])

    def test_a_tagged_digest_with_no_binding_is_not_checkable(self):
        entries = self.ledger()
        bundle = build_bundle(entries, {})
        result = verify_bundle(bundle)
        self.assertFalse(result.ok)
        self.assertEqual(result.state, UNMEASURABLE)
        self.assertIn("BINDING-UNMEASURABLE", [brk.code for brk in result.breaks])

    def test_a_binding_without_a_fingerprint_is_not_checkable(self):
        bundle = self.bundle()
        for binding in bundle["bindings"]:
            binding["manifest_sha256"] = ""
        result = verify_bundle(bundle)
        self.assertEqual(result.state, UNMEASURABLE)

    def test_a_binding_for_a_row_that_is_not_in_the_bundle_is_a_mismatch(self):
        bundle = self.bundle()
        bundle["bindings"].append(dict(bundle["bindings"][0], seq=99))
        result = verify_bundle(bundle)
        self.assertEqual(result.state, MISMATCH)
        self.assertIn("BINDING-ORPHAN", [brk.code for brk in result.breaks])

    def test_a_declared_posture_the_records_do_not_earn_diverges(self):
        bundle = self.bundle(verifier="")
        bundle["audit"]["severity"] = "PASS"
        bundle["audit"]["findings"] = []
        result = verify_bundle(bundle)
        self.assertFalse(result.ok)
        self.assertIn("AUDIT-DIVERGES", [brk.code for brk in result.breaks])

    def test_the_manifest_leg_is_named_as_unprovable_off_machine(self):
        result = verify_bundle(self.bundle())
        self.assertTrue(result.ok, result.breaks)
        self.assertIn("MANIFEST-NOT-BUNDLED", [brk.code for brk in result.breaks])

    def test_a_chain_break_still_fails_the_bundle(self):
        bundle = self.bundle()
        bundle["entries"][0]["record"]["outcome"] = "FORGED"
        result = verify_bundle(bundle)
        self.assertFalse(result.ok)
        self.assertIn("HASH-MISMATCH", [brk.code for brk in result.breaks])


class TestOldBundlesAreNotClean(_LedgerCase):
    def test_a_v1_bundle_is_not_checkable_not_clean(self):
        bundle = self.bundle()
        bundle["format"] = BUNDLE_FORMAT_V1
        for key in ("bindings", "audit"):
            bundle.pop(key, None)
        result = verify_bundle(bundle)
        self.assertFalse(result.ok)
        self.assertEqual(result.state, BINDINGS_ABSENT)
        self.assertIn("BINDINGS-ABSENT", [brk.code for brk in result.breaks])

    def test_a_v1_bundle_is_not_a_format_mismatch(self):
        bundle = self.bundle()
        bundle["format"] = BUNDLE_FORMAT_V1
        result = verify_bundle(bundle)
        self.assertNotIn("FORMAT-MISMATCH", [brk.code for brk in result.breaks])

    def test_a_v2_bundle_with_null_bindings_is_not_checkable(self):
        bundle = build_bundle(self.ledger(), None)
        self.assertIsNone(bundle["bindings"])
        result = verify_bundle(bundle)
        self.assertEqual(result.state, BINDINGS_ABSENT)


class TestHostileArtifacts(_LedgerCase):
    """The bundle is attacker-reachable: a malformed binding is a finding, never a crash."""

    def test_a_binding_that_is_not_an_object_is_a_mismatch(self):
        bundle = self.bundle()
        bundle["bindings"].append("not-a-binding")
        result = verify_bundle(bundle)
        self.assertEqual(result.state, MISMATCH)
        self.assertIn("BINDING-MISMATCH", [brk.code for brk in result.breaks])

    def test_a_binding_without_an_integer_seq_is_a_mismatch(self):
        bundle = self.bundle()
        bundle["bindings"][0]["seq"] = "zero"
        result = verify_bundle(bundle)
        self.assertEqual(result.state, MISMATCH)

    def test_a_duplicate_binding_is_a_mismatch(self):
        bundle = self.bundle()
        bundle["bindings"].append(dict(bundle["bindings"][0]))
        result = verify_bundle(bundle)
        self.assertEqual(result.state, MISMATCH)
        self.assertIn("BINDING-DUPLICATE", [brk.code for brk in result.breaks])

    def test_a_fingerprint_that_is_not_a_sha256_is_a_mismatch(self):
        bundle = self.bundle()
        bundle["bindings"][0]["manifest_sha256"] = "deadbeef"
        result = verify_bundle(bundle)
        self.assertEqual(result.state, MISMATCH)
        self.assertIn("BINDING-MISMATCH", [brk.code for brk in result.breaks])

    def test_a_bundle_without_a_declared_audit_is_not_checkable(self):
        bundle = self.bundle()
        bundle.pop("audit")
        result = verify_bundle(bundle)
        self.assertEqual(result.state, UNMEASURABLE)
        self.assertIn("AUDIT-ABSENT", [brk.code for brk in result.breaks])


class TestCliContract(_LedgerCase):
    def _run(self, argv):
        out = io.StringIO()
        with redirect_stdout(out):
            code = cli.main(argv)
        return code, out.getvalue()

    def test_export_embeds_bindings_and_verify_bundle_passes(self):
        self.ledger()
        out_path = os.path.join(self.dir, "audit.bundle.json")
        code, _ = self._run(["export", "--ledger", self.path, "--out", out_path])
        self.assertEqual(code, 0)
        self.assertEqual(len(read_bundle(out_path)["bindings"]), 2)

        code, text = self._run(["verify-bundle", out_path])
        self.assertEqual(code, 0, text)
        self.assertIn("BINDINGS-PRESENT", text)

    def test_verify_bundle_reports_mismatch_as_exit_1(self):
        self.ledger()
        out_path = os.path.join(self.dir, "audit.bundle.json")
        self._run(["export", "--ledger", self.path, "--out", out_path])
        bundle = read_bundle(out_path)
        bundle["bindings"][0]["model_digest"] = "ws1:" + ("c" * 64)
        write_bundle(out_path, bundle)

        code, text = self._run(["verify-bundle", out_path])
        self.assertEqual(code, 1, text)
        self.assertIn("BINDING-MISMATCH", text)

    def test_no_provenance_export_declares_itself_incomplete_and_exits_2(self):
        self.ledger()
        out_path = os.path.join(self.dir, "chain-only.bundle.json")
        code, _ = self._run(
            ["export", "--ledger", self.path, "--out", out_path, "--no-provenance"]
        )
        self.assertEqual(code, 0)
        bundle = read_bundle(out_path)
        self.assertIsNone(bundle["bindings"])
        self.assertEqual(bundle["provenance"], "absent")

        code, text = self._run(["verify-bundle", out_path])
        self.assertEqual(code, 2, text)
        self.assertIn("BINDINGS-ABSENT", text)

    def test_verify_bundle_json_carries_the_state_and_the_checks(self):
        self.ledger()
        out_path = os.path.join(self.dir, "audit.bundle.json")
        self._run(["export", "--ledger", self.path, "--out", out_path])
        code, text = self._run(["verify-bundle", out_path, "--json"])
        self.assertEqual(code, 0)
        payload = json.loads(text)
        self.assertEqual(payload["state"], PASS)
        self.assertEqual(len(payload["bindings"]), 2)
        self.assertEqual(payload["audit"]["total"], 2)


if __name__ == "__main__":
    unittest.main()
