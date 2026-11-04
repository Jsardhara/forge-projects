import os
import struct
import tempfile
import unittest

from fixtures import gbytes, write_safetensors

from wsaudit import diff
from wsaudit.errors import WsAuditError


def f32(*values):
    return struct.pack("<%df" % len(values), *values)


class LoraNameTest(unittest.TestCase):
    def test_maps_a_and_b_sides_to_target(self):
        target, side = diff.map_lora_name(
            "base_model.model.model.layers.12.self_attn.q_proj.lora_A.weight"
        )
        self.assertEqual(target, "model.layers.12.self_attn.q_proj")
        self.assertEqual(side, "A")

    def test_maps_default_suffix(self):
        target, side = diff.map_lora_name(
            "base_model.model.model.layers.0.mlp.down_proj.lora_B.default.weight"
        )
        self.assertEqual(target, "model.layers.0.mlp.down_proj")
        self.assertEqual(side, "B")

    def test_maps_kohya_down_up_naming(self):
        # The real LoRAs on this host use lora_down/lora_up, not lora_A/lora_B.
        target, side = diff.map_lora_name(
            "text_encoders.transformer.model.embed_tokens.lora_down.weight"
        )
        self.assertEqual(target, "text_encoders.transformer.model.embed_tokens")
        self.assertEqual(side, "A")
        _, side_up = diff.map_lora_name(
            "text_encoders.transformer.model.embed_tokens.lora_up.weight"
        )
        self.assertEqual(side_up, "B")

    def test_plain_weights_are_not_lora(self):
        self.assertIsNone(diff.map_lora_name("model.layers.0.mlp.down_proj.weight"))


class DiffTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def _path(self, name):
        return os.path.join(self.dir, name)

    def test_identical_models_have_no_rows(self):
        a = write_safetensors(self._path("a.safetensors"), [("w", "F32", [2], f32(1, 2))])
        b = write_safetensors(self._path("b.safetensors"), [("w", "F32", [2], f32(1, 2))])
        report = diff.diff_models(a, b)
        self.assertEqual(report.rows, ())
        self.assertEqual(report.changed, 0)

    def test_l2_and_relative_norm_are_computed(self):
        a = write_safetensors(self._path("a.safetensors"), [("w", "F32", [2], f32(1, 2))])
        b = write_safetensors(self._path("b.safetensors"), [("w", "F32", [2], f32(2, 4))])
        row = diff.diff_models(a, b).rows[0]
        self.assertEqual(row.change, "changed")
        self.assertAlmostEqual(row.l2, 5 ** 0.5, places=6)
        self.assertAlmostEqual(row.rel_norm, 1.0, places=6)

    def test_added_and_removed_are_reported(self):
        a = write_safetensors(
            self._path("a.safetensors"),
            [("keep", "F32", [1], f32(1)), ("gone", "F32", [1], f32(2))],
        )
        b = write_safetensors(
            self._path("b.safetensors"),
            [("keep", "F32", [1], f32(1)), ("new", "F32", [1], f32(3))],
        )
        report = diff.diff_models(a, b)
        by_name = {row.name: row.change for row in report.rows}
        self.assertEqual(by_name, {"gone": "removed", "new": "added"})
        self.assertEqual(report.added, 1)
        self.assertEqual(report.removed, 1)
        self.assertEqual(report.changed, 0)

    def test_shape_change_reports_without_l2(self):
        a = write_safetensors(self._path("a.safetensors"), [("w", "F32", [2], f32(1, 2))])
        b = write_safetensors(self._path("b.safetensors"), [("w", "F32", [4], f32(1, 2, 3, 4))])
        row = diff.diff_models(a, b).rows[0]
        self.assertEqual(row.change, "changed")
        self.assertIsNone(row.l2)

    def test_quantised_payload_has_no_l2(self):
        a = write_safetensors(self._path("a.safetensors"), [("w", "I8", [2], gbytes(2, 1))])
        b = write_safetensors(self._path("b.safetensors"), [("w", "I8", [2], gbytes(2, 2))])
        row = diff.diff_models(a, b).rows[0]
        self.assertEqual(row.change, "changed")
        self.assertIsNone(row.l2)

    def test_lora_adapter_is_mapped_to_its_module(self):
        base = write_safetensors(
            self._path("base.safetensors"),
            [("model.layers.0.q_proj.weight", "F32", [2], f32(1, 2))],
        )
        adapter = write_safetensors(
            self._path("adapter.safetensors"),
            [
                ("base_model.model.model.layers.0.q_proj.lora_A.weight", "F32", [2, 2],
                 f32(0.1, 0.2, 0.3, 0.4)),
                ("base_model.model.model.layers.0.q_proj.lora_B.weight", "F32", [2, 2],
                 f32(0.0, 0.1, 0.2, 0.0)),
            ],
        )
        report = diff.diff_models(base, adapter, lora_map=True)
        self.assertEqual(len(report.rows), 2)
        self.assertEqual({row.change for row in report.rows}, {"patched"})
        names = " ".join(row.name for row in report.rows)
        self.assertIn("model.layers.0.q_proj", names)
        self.assertIn("lora_A", names)
        self.assertIn("lora_B", names)

    def test_adapter_only_base_is_labelled_not_blank(self):
        # Diffing two LoRA files: the base has no <module>.weight to compare, so
        # the row must say "adapter", never an empty left-hand side.
        base = write_safetensors(
            self._path("base.safetensors"),
            [("unrelated.weight", "F32", [1], f32(0.0))],
        )
        adapter = write_safetensors(
            self._path("adapter.safetensors"),
            [("model.layers.0.q_proj.lora_down.weight", "F32", [1, 2], f32(0.1, 0.2))],
        )
        row = diff.diff_models(base, adapter, lora_map=True).rows[0]
        self.assertEqual(row.name, "model.layers.0.q_proj (lora_A)")
        self.assertEqual(row.dtype_base, "adapter")

    def test_ranked_rows_put_biggest_change_first(self):
        a = write_safetensors(
            self._path("a.safetensors"),
            [("small", "F32", [1], f32(1.0)), ("big", "F32", [1], f32(1.0))],
        )
        b = write_safetensors(
            self._path("b.safetensors"),
            [("small", "F32", [1], f32(1.1)), ("big", "F32", [1], f32(9.0))],
        )
        rows = diff.diff_models(a, b).rows
        self.assertEqual(rows[0].name, "big")

    def test_missing_file_is_an_audit_error(self):
        with self.assertRaises(WsAuditError):
            diff.diff_models(self._path("nope"), self._path("also-nope"))


if __name__ == "__main__":
    unittest.main()
