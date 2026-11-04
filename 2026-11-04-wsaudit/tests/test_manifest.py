import json
import os
import tempfile
import unittest

from fixtures import gbytes, write_safetensors

from wsaudit import digest, manifest
from wsaudit.errors import WsAuditError


class ManifestTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name
        self.path = os.path.join(self.dir, "a.safetensors")
        write_safetensors(self.path, [("w", "F32", [2], gbytes(8, 1))])
        self.model = digest.digest_model(self.path)

    def tearDown(self):
        self.tmp.cleanup()

    def test_build_records_every_tensor(self):
        built = manifest.build_manifest(self.model)
        self.assertEqual(built["tool"], "wsaudit")
        self.assertEqual(built["model_digest"], self.model.model_digest)
        self.assertEqual(list(built["tensors"]), ["w"])
        self.assertEqual(len(built["tensors"]["w"]["sha256"]), 64)
        self.assertFalse(built["partial"])

    def test_save_and_load_roundtrip(self):
        target = os.path.join(self.dir, "wsaudit.json")
        manifest.save_manifest(manifest.build_manifest(self.model), target)
        loaded = manifest.load_manifest(target)
        self.assertEqual(loaded["model_digest"], self.model.model_digest)

    def test_matching_manifest_compares_ok(self):
        result = manifest.compare(self.model, manifest.build_manifest(self.model))
        self.assertTrue(result.ok)
        self.assertEqual(result.problems, ())
        self.assertEqual(result.checked, 1)

    def test_substituted_weights_are_detected(self):
        other = os.path.join(self.dir, "b.safetensors")
        write_safetensors(other, [("w", "F32", [2], gbytes(8, 9))])
        result = manifest.compare(digest.digest_model(other), manifest.build_manifest(self.model))
        self.assertFalse(result.ok)
        self.assertTrue(any("model digest" in p for p in result.problems))

    def test_single_tensor_mismatch_names_the_tensor(self):
        tampered = manifest.build_manifest(self.model)
        tampered["tensors"]["w"]["sha256"] = "0" * 64
        result = manifest.compare(self.model, tampered)
        self.assertFalse(result.ok)
        self.assertTrue(any("w" in p for p in result.problems))

    def test_added_tensor_is_detected(self):
        wider = os.path.join(self.dir, "c.safetensors")
        write_safetensors(
            wider,
            [("w", "F32", [2], gbytes(8, 1)), ("extra", "F32", [1], gbytes(4, 3))],
        )
        result = manifest.compare(digest.digest_model(wider), manifest.build_manifest(self.model))
        self.assertFalse(result.ok)
        self.assertTrue(any("extra" in p for p in result.problems))

    def test_removed_tensor_is_detected(self):
        narrower = os.path.join(self.dir, "d.safetensors")
        write_safetensors(narrower, [("other", "F32", [2], gbytes(8, 1))])
        result = manifest.compare(digest.digest_model(narrower), manifest.build_manifest(self.model))
        self.assertFalse(result.ok)
        self.assertTrue(any("missing" in p for p in result.problems))

    def test_partial_model_cannot_be_verified(self):
        partial = digest.digest_model(self.path, header_only=True)
        result = manifest.compare(partial, manifest.build_manifest(self.model))
        self.assertFalse(result.ok)
        self.assertTrue(any("partial" in p for p in result.problems))

    def test_bad_json_is_an_audit_error(self):
        target = os.path.join(self.dir, "bad.json")
        with open(target, "w") as fh:
            fh.write("{not json")
        with self.assertRaises(WsAuditError):
            manifest.load_manifest(target)

    def test_missing_keys_is_an_audit_error(self):
        target = os.path.join(self.dir, "keys.json")
        with open(target, "w") as fh:
            json.dump({"tool": "wsaudit"}, fh)
        with self.assertRaises(WsAuditError):
            manifest.load_manifest(target)


if __name__ == "__main__":
    unittest.main()
