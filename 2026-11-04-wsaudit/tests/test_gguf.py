import os
import struct
import tempfile
import unittest

from fixtures import GGML_TYPES, gguf_tensor, write_gguf

from wsaudit import gguf
from wsaudit.errors import WsAuditError


class GgufParseTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def _path(self, name="m.gguf"):
        return os.path.join(self.dir, name)

    def test_reads_magic_version_and_counts(self):
        path = write_gguf(
            self._path(),
            [("blk.0.attn_q.weight", 0, [4, 2], gguf_tensor(0, [4, 2]))],
            kv=[("general.architecture", (8, "qwen3")), ("general.alignment", (4, 32))],
        )
        parsed = gguf.parse(path)
        self.assertEqual(parsed.format, "gguf")
        self.assertEqual(parsed.version, 3)
        self.assertEqual(parsed.kv["general.architecture"], "qwen3")
        self.assertEqual(len(parsed.tensors), 1)

    def test_tensor_shape_and_dtype(self):
        raw = gguf_tensor(0, [4, 2], seed=1)
        path = write_gguf(self._path(), [("w", 0, [4, 2], raw)])
        tensor = gguf.parse(path).tensors[0]
        self.assertEqual(tensor.name, "w")
        self.assertEqual(tensor.dtype, "F32")
        self.assertEqual(tensor.shape, (4, 2))
        self.assertEqual(tensor.elements, 8)
        self.assertEqual(tensor.nbytes, len(raw))

    def test_quantised_tensor_size_uses_block_table(self):
        raw = gguf_tensor(12, [2, 256], seed=2)      # Q4_K: 256 elem / 144 bytes
        path = write_gguf(self._path(), [("w", 12, [2, 256], raw)])
        tensor = gguf.parse(path).tensors[0]
        self.assertEqual(tensor.dtype, "Q4_K")
        self.assertEqual(tensor.nbytes, 288)

    def test_tensor_data_offsets_are_absolute_and_aligned(self):
        first = gguf_tensor(0, [4], seed=3)
        second = gguf_tensor(1, [8], seed=4)
        path = write_gguf(self._path(), [("a", 0, [4], first), ("b", 1, [8], second)])
        parsed = gguf.parse(path)
        with open(path, "rb") as fh:
            blob = fh.read()
        a, b = parsed.tensors
        self.assertEqual(a.offset % parsed.alignment, 0)
        self.assertEqual(blob[a.offset:a.offset + len(first)], first)
        self.assertEqual(blob[b.offset:b.offset + len(second)], second)

    def test_kv_types_string_uint_bool_float_array(self):
        path = write_gguf(
            self._path(),
            [("w", 0, [1], gguf_tensor(0, [1]))],
            kv=[
                ("s", (8, "hello")),
                ("u", (4, 7)),
                ("b", (7, True)),
                ("f", (6, 1.5)),
                ("a", (9, ["x", "y"])),
            ],
        )
        kv = gguf.parse(path).kv
        self.assertEqual(kv["s"], "hello")
        self.assertEqual(kv["u"], 7)
        self.assertIs(kv["b"], True)
        self.assertAlmostEqual(kv["f"], 1.5, places=6)
        self.assertEqual(kv["a"], ["x", "y"])

    def test_rejects_unknown_ggml_type(self):
        path = write_gguf(self._path(), [("w", 250, [1], b"\x00" * 4)])
        with self.assertRaises(WsAuditError):
            gguf.parse(path)

    def test_huge_tokenizer_array_is_summarised_not_stored(self):
        vocab = ["tok%d" % i for i in range(5000)]
        path = write_gguf(
            self._path("vocab.gguf"),
            [("w", 0, [1], gguf_tensor(0, [1]))],
            kv=[("tokenizer.ggml.tokens", (9, vocab))],
        )
        self.assertEqual(gguf.parse(path).kv["tokenizer.ggml.tokens"], "<array of 5000>")

    def test_rejects_unknown_metadata_value_type(self):
        path = self._path("vtype.gguf")
        meta = b"GGUF" + struct.pack("<IQQ", 3, 0, 1)
        meta += struct.pack("<Q", 2) + b"kv" + struct.pack("<I", 200) + b"\x00" * 32
        with open(path, "wb") as fh:
            fh.write(meta)
        with self.assertRaises(WsAuditError):
            gguf.parse(path)

    def test_alignment_from_kv_is_honoured(self):
        path = write_gguf(
            self._path(),
            [("w", 0, [1], gguf_tensor(0, [1]))],
            kv=[("general.alignment", (4, 64))],
        )
        parsed = gguf.parse(path)
        self.assertEqual(parsed.alignment, 64)
        self.assertEqual(parsed.tensors[0].offset % 64, 0)

    def test_rejects_bad_magic(self):
        path = self._path("bad.gguf")
        with open(path, "wb") as fh:
            fh.write(b"GGML" + b"\x00" * 32)
        with self.assertRaises(WsAuditError):
            gguf.parse(path)

    def test_rejects_unsupported_version(self):
        path = self._path("v1.gguf")
        with open(path, "wb") as fh:
            fh.write(b"GGUF" + struct.pack("<IQQ", 1, 0, 0) + b"\x00" * 32)
        with self.assertRaises(WsAuditError):
            gguf.parse(path)

    def test_rejects_truncated_tensor_info(self):
        path = self._path("cut.gguf")
        meta = b"GGUF" + struct.pack("<IQQ", 3, 4, 0)
        with open(path, "wb") as fh:
            fh.write(meta)
        with self.assertRaises(WsAuditError):
            gguf.parse(path)

    def test_rejects_tensor_bytes_past_eof(self):
        path = write_gguf(self._path(), [("w", 0, [64], gguf_tensor(0, [64]))])
        with open(path, "r+b") as fh:
            fh.truncate(os.path.getsize(path) - 8)
        with self.assertRaises(WsAuditError):
            gguf.parse(path)

    def test_elements_must_divide_block_size(self):
        path = write_gguf(self._path(), [("w", 12, [10], b"\x00" * 144)])
        with self.assertRaises(WsAuditError):
            gguf.parse(path)

    def test_type_table_matches_spec_facts(self):
        self.assertEqual(GGML_TYPES[12][1:], (256, 144))
        self.assertEqual(GGML_TYPES[1][1:], (1, 2))


if __name__ == "__main__":
    unittest.main()
