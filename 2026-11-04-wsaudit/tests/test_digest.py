import os
import tempfile
import unittest

from fixtures import gguf_tensor, gbytes, write_gguf, write_safetensors

from wsaudit import digest
from wsaudit.errors import WsAuditError
from wsaudit.models import TensorDigest


def td(name, sha, dtype="F32", shape=(1,)):
    return TensorDigest(name=name, dtype=dtype, shape=shape, sha256=sha)


class CanonicalDigestTest(unittest.TestCase):
    def test_order_independent(self):
        a = [td("x", "aa"), td("y", "bb")]
        self.assertEqual(digest.canonical_digest(a), digest.canonical_digest(list(reversed(a))))

    def test_sensitive_to_tensor_hash(self):
        self.assertNotEqual(
            digest.canonical_digest([td("x", "aa")]),
            digest.canonical_digest([td("x", "ab")]),
        )

    def test_sensitive_to_name_dtype_shape(self):
        base = digest.canonical_digest([td("x", "aa")])
        self.assertNotEqual(base, digest.canonical_digest([td("x2", "aa")]))
        self.assertNotEqual(base, digest.canonical_digest([td("x", "aa", "F16")]))
        self.assertNotEqual(base, digest.canonical_digest([td("x", "aa", shape=(2,))]))

    def test_no_boundary_collision(self):
        # "a|b" + "c" must not hash the same as "a" + "b|c"
        left = digest.canonical_digest([td("a|b", "cc")])
        right = digest.canonical_digest([td("a", "bb|cc")])
        self.assertNotEqual(left, right)

    def test_empty_set_is_stable(self):
        self.assertEqual(digest.canonical_digest([]), digest.canonical_digest([]))
        self.assertEqual(len(digest.canonical_digest([])), 64)

    def test_partial_digest_is_marked(self):
        full = digest.canonical_digest([td("x", "aa")])
        partial = digest.canonical_digest([td("x", None)], partial=True)
        self.assertNotEqual(full, partial)


class DigestModelTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def test_safetensors_digest_is_reproducible(self):
        path = write_safetensors(
            os.path.join(self.dir, "a.safetensors"),
            [("w", "F32", [2], gbytes(8, 5))],
        )
        first = digest.digest_model(path)
        second = digest.digest_model(path)
        self.assertEqual(first.model_digest, second.model_digest)
        self.assertEqual(first.tensor_count, 1)
        self.assertEqual(len(first.tensors[0].sha256), 64)
        self.assertFalse(first.partial)

    def test_tensor_hash_tracks_payload(self):
        one = write_safetensors(
            os.path.join(self.dir, "one.safetensors"), [("w", "F32", [2], gbytes(8, 1))]
        )
        two = write_safetensors(
            os.path.join(self.dir, "two.safetensors"), [("w", "F32", [2], gbytes(8, 2))]
        )
        self.assertNotEqual(
            digest.digest_model(one).model_digest, digest.digest_model(two).model_digest
        )
        self.assertNotEqual(
            digest.digest_model(one).tensors[0].sha256,
            digest.digest_model(two).tensors[0].sha256,
        )

    def test_metadata_only_change_keeps_tensor_hash(self):
        one = write_safetensors(
            os.path.join(self.dir, "m1.safetensors"),
            [("w", "F32", [2], gbytes(8, 1))],
            metadata={"format": "pt"},
        )
        two = write_safetensors(
            os.path.join(self.dir, "m2.safetensors"),
            [("w", "F32", [2], gbytes(8, 1))],
            metadata={"format": "mlx"},
        )
        self.assertEqual(
            digest.digest_model(one).model_digest, digest.digest_model(two).model_digest
        )

    def test_header_only_marks_partial_and_skips_data_hash(self):
        path = write_safetensors(
            os.path.join(self.dir, "h.safetensors"), [("w", "F32", [2], gbytes(8, 1))]
        )
        model = digest.digest_model(path, header_only=True)
        self.assertTrue(model.partial)
        self.assertIsNone(model.tensors[0].sha256)
        self.assertNotEqual(model.model_digest, digest.digest_model(path).model_digest)

    def test_gguf_digest(self):
        path = write_gguf(
            os.path.join(self.dir, "a.gguf"),
            [("w", 12, [256], gguf_tensor(12, [256], seed=9))],
        )
        model = digest.digest_model(path)
        self.assertEqual(model.format, "gguf")
        self.assertEqual(model.tensors[0].dtype, "Q4_K")
        self.assertEqual(model.tensor_count, 1)

    def test_unknown_format_is_an_error(self):
        path = os.path.join(self.dir, "x.bin")
        with open(path, "wb") as fh:
            fh.write(b"not a model" * 8)
        with self.assertRaises(WsAuditError):
            digest.digest_model(path)

    def test_truncated_model_never_returns_a_clean_digest(self):
        path = write_safetensors(
            os.path.join(self.dir, "t.safetensors"), [("w", "F32", [4], gbytes(16, 1))]
        )
        with open(path, "r+b") as fh:
            fh.truncate(os.path.getsize(path) - 4)
        with self.assertRaises(WsAuditError):
            digest.digest_model(path)


if __name__ == "__main__":
    unittest.main()
