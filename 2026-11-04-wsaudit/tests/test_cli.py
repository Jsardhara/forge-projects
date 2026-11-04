import io
import json
import os
import struct
import tempfile
import unittest
from contextlib import redirect_stdout

from fixtures import gbytes, write_safetensors

from wsaudit.cli import main


def f32(*values):
    return struct.pack("<%df" % len(values), *values)


class CliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name
        self.model = write_safetensors(
            os.path.join(self.dir, "m.safetensors"), [("w", "F32", [2], f32(1, 2))]
        )
        self.manifest = os.path.join(self.dir, "m.json")

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, argv):
        out = io.StringIO()
        with redirect_stdout(out):
            code = main(argv)
        return code, out.getvalue()

    def _write_manifest(self):
        code, _ = self._run(["hash", self.model, "--manifest-out", self.manifest])
        self.assertEqual(code, 0)
        return self.manifest

    def test_hash_json_is_machine_readable(self):
        code, out = self._run(["hash", self.model, "--json"])
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertEqual(payload["format"], "safetensors")
        self.assertEqual(payload["tensor_count"], 1)
        self.assertEqual(len(payload["model_digest"]), 64)

    def test_hash_text_mentions_digest_and_path(self):
        code, out = self._run(["hash", self.model])
        self.assertEqual(code, 0)
        self.assertIn("m.safetensors", out)
        self.assertIn("w", out)

    def test_manifest_out_then_verify_is_clean(self):
        self._write_manifest()
        code, out = self._run(["hash", self.model, "--manifest", self.manifest])
        self.assertEqual(code, 0)
        self.assertIn("verified", out.lower())

    def test_manifest_out_then_verify_detects_substitution(self):
        self._write_manifest()
        swapped = write_safetensors(
            os.path.join(self.dir, "swapped.safetensors"), [("w", "F32", [2], f32(1, 9))]
        )
        code, out = self._run(["hash", swapped, "--manifest", self.manifest])
        self.assertEqual(code, 1)
        self.assertIn("MISMATCH", out.upper())

    def test_missing_model_exits_2(self):
        code, out = self._run(["hash", os.path.join(self.dir, "nope.safetensors")])
        self.assertEqual(code, 2)
        self.assertIn("could not measure", out.lower())

    def test_unknown_format_exits_2(self):
        junk = os.path.join(self.dir, "junk.bin")
        with open(junk, "wb") as fh:
            fh.write(b"\x00" * 64)
        code, out = self._run(["hash", junk])
        self.assertEqual(code, 2)
        self.assertIn("could not measure", out.lower())

    def test_header_only_is_partial(self):
        code, out = self._run(["hash", self.model, "--header-only", "--json"])
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertTrue(payload["partial"])
        self.assertIsNone(payload["tensors"][0]["sha256"])

    def test_header_only_cannot_satisfy_a_manifest(self):
        self._write_manifest()
        code, out = self._run(["hash", self.model, "--header-only", "--manifest", self.manifest])
        self.assertEqual(code, 2)
        self.assertIn("partial", out.lower())

    def test_diff_identical_exits_0(self):
        code, out = self._run(["diff", self.model, self.model])
        self.assertEqual(code, 0)
        self.assertIn("identical", out.lower())

    def test_diff_changed_exits_1(self):
        other = write_safetensors(
            os.path.join(self.dir, "o.safetensors"), [("w", "F32", [2], f32(3, 4))]
        )
        code, out = self._run(["diff", self.model, other])
        self.assertEqual(code, 1)
        self.assertIn("w", out)

    def test_diff_json_lists_rows(self):
        other = write_safetensors(
            os.path.join(self.dir, "o.safetensors"), [("w", "F32", [2], f32(3, 4))]
        )
        code, out = self._run(["diff", self.model, other, "--json"])
        self.assertEqual(code, 1)
        payload = json.loads(out)
        self.assertEqual(payload["changed"], 1)
        self.assertEqual(payload["rows"][0]["name"], "w")

    def test_diff_missing_file_exits_2(self):
        code, _ = self._run(["diff", self.model, os.path.join(self.dir, "nope")])
        self.assertEqual(code, 2)

    def test_quiet_suppresses_text_but_keeps_exit_code(self):
        code, out = self._run(["hash", self.model, "--quiet"])
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "")

    def test_no_arguments_exits_2(self):
        code, _ = self._run([])
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
