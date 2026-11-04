import json
import os
import struct
import tempfile
import unittest

from fixtures import gbytes, write_safetensors

from wsaudit import safetensors
from wsaudit.errors import WsAuditError


class SafetensorsHeaderTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def _path(self, name="m.safetensors"):
        return os.path.join(self.dir, name)

    def test_parses_two_tensors_with_offsets(self):
        path = write_safetensors(
            self._path(),
            [
                ("a.weight", "F32", [2], gbytes(8, 1)),
                ("b.weight", "F16", [4], gbytes(8, 2)),
            ],
        )
        parsed = safetensors.parse(path)
        self.assertEqual(parsed.format, "safetensors")
        self.assertEqual([t.name for t in parsed.tensors], ["a.weight", "b.weight"])
        first, second = parsed.tensors
        self.assertEqual(first.dtype, "F32")
        self.assertEqual(first.shape, (2,))
        self.assertEqual(first.nbytes, 8)
        self.assertEqual(second.offset, first.offset + 8)
        self.assertEqual(parsed.total_bytes, 16)

    def test_data_offsets_are_absolute(self):
        path = write_safetensors(self._path(), [("w", "F32", [1], gbytes(4, 3))])
        parsed = safetensors.parse(path)
        with open(path, "rb") as fh:
            blob = fh.read()
        start = parsed.tensors[0].offset
        self.assertEqual(blob[start:start + 4], gbytes(4, 3))

    def test_metadata_key_is_not_a_tensor(self):
        path = write_safetensors(
            self._path(), [("w", "F32", [1], gbytes(4))], metadata={"format": "pt"}
        )
        parsed = safetensors.parse(path)
        self.assertEqual([t.name for t in parsed.tensors], ["w"])
        self.assertEqual(parsed.metadata["format"], "pt")

    def test_metadata_alone_yields_no_tensors(self):
        path = write_safetensors(self._path(), [], metadata={"format": "pt"})
        parsed = safetensors.parse(path)
        self.assertEqual(parsed.tensors, ())
        self.assertEqual(parsed.total_bytes, 0)

    def test_rejects_missing_file(self):
        with self.assertRaises(WsAuditError):
            safetensors.parse(os.path.join(self.dir, "nope.safetensors"))

    def test_identifies_a_zip_container_by_name(self):
        # Found on this host: a PEFT adapter shipped as a torch.save zip under a
        # .safetensors name. The error must say what the file actually is.
        path = self._path("zip.safetensors")
        with open(path, "wb") as fh:
            fh.write(b"PK\x03\x04" + b"\x00" * 60)
        with self.assertRaises(WsAuditError) as caught:
            safetensors.parse(path)
        self.assertIn("zip", str(caught.exception).lower())

    def test_rejects_truncated_header(self):
        path = self._path("short.safetensors")
        with open(path, "wb") as fh:
            fh.write(struct.pack("<Q", 4096) + b"{}")
        with self.assertRaises(WsAuditError):
            safetensors.parse(path)

    def test_rejects_non_json_header(self):
        path = self._path("bad.safetensors")
        payload = b"not json at all"
        with open(path, "wb") as fh:
            fh.write(struct.pack("<Q", len(payload)) + payload)
        with self.assertRaises(WsAuditError):
            safetensors.parse(path)

    def test_rejects_offsets_past_end_of_file(self):
        path = self._path("clipped.safetensors")
        header = {"w": {"dtype": "F32", "shape": [4], "data_offsets": [0, 16]}}
        raw = json.dumps(header).encode()
        with open(path, "wb") as fh:
            fh.write(struct.pack("<Q", len(raw)) + raw + b"\x00\x00")
        with self.assertRaises(WsAuditError):
            safetensors.parse(path)

    def test_rejects_inverted_offsets(self):
        path = self._path("inverted.safetensors")
        header = {"w": {"dtype": "F32", "shape": [4], "data_offsets": [8, 4]}}
        raw = json.dumps(header).encode()
        with open(path, "wb") as fh:
            fh.write(struct.pack("<Q", len(raw)) + raw + b"\x00" * 8)
        with self.assertRaises(WsAuditError):
            safetensors.parse(path)

    def test_rejects_missing_entry_fields(self):
        path = self._path("fields.safetensors")
        header = {"w": {"dtype": "F32", "shape": [4]}}
        raw = json.dumps(header).encode()
        with open(path, "wb") as fh:
            fh.write(struct.pack("<Q", len(raw)) + raw + b"\x00" * 16)
        with self.assertRaises(WsAuditError):
            safetensors.parse(path)

    def test_unknown_dtype_is_rejected(self):
        path = write_safetensors(self._path(), [("w", "FLOAT64_X", [1], gbytes(8))])
        with self.assertRaises(WsAuditError):
            safetensors.parse(path)

    def test_nbytes_must_match_declared_shape(self):
        path = write_safetensors(self._path(), [("w", "F32", [4], gbytes(8))])
        with self.assertRaises(WsAuditError):
            safetensors.parse(path)


if __name__ == "__main__":
    unittest.main()
