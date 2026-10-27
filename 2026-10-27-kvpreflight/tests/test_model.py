"""Parsing a real model config.json without transformers installed."""

import json
import os
import tempfile
import unittest

from kvpreflight.model import ConfigError, load_model_shape


def write_config(tmp, payload, extra_files=None):
    with open(os.path.join(tmp, "config.json"), "w", encoding="utf-8") as fh:
        json.dump(payload, fh)
    for name, size in (extra_files or {}).items():
        with open(os.path.join(tmp, name), "wb") as fh:
            fh.write(b"\0" * size)
    return tmp


QWEN25_AWQ = {
    "architectures": ["Qwen2ForCausalLM"],
    "num_hidden_layers": 28,
    "num_attention_heads": 28,
    "num_key_value_heads": 4,
    "hidden_size": 3584,
    "torch_dtype": "float16",
    "max_position_embeddings": 32768,
    "quantization_config": {"bits": 4, "quant_method": "awq"},
}


class TestLoadModelShape(unittest.TestCase):
    def test_head_dim_derived_when_absent(self):
        # Real Qwen2.5-7B config has no head_dim; 3584 / 28 heads = 128.
        with tempfile.TemporaryDirectory() as tmp:
            shape = load_model_shape(write_config(tmp, QWEN25_AWQ))
        self.assertEqual(shape.head_dim, 128)
        self.assertEqual(shape.layers, 28)
        self.assertEqual(shape.kv_heads, 4)
        self.assertEqual(shape.dtype, "float16")

    def test_kv_heads_default_to_attention_heads(self):
        payload = {
            "num_hidden_layers": 12,
            "num_attention_heads": 8,
            "hidden_size": 1024,
            "torch_dtype": "float32",
        }
        with tempfile.TemporaryDirectory() as tmp:
            shape = load_model_shape(write_config(tmp, payload))
        self.assertEqual(shape.kv_heads, 8)
        self.assertEqual(shape.head_dim, 128)

    def test_head_dim_preferred_over_derivation(self):
        payload = {
            "num_hidden_layers": 28,
            "num_attention_heads": 16,
            "num_key_value_heads": 8,
            "head_dim": 128,
            "hidden_size": 2048,
            "torch_dtype": "bfloat16",
        }
        with tempfile.TemporaryDirectory() as tmp:
            shape = load_model_shape(write_config(tmp, payload))
        self.assertEqual(shape.head_dim, 128)

    def test_missing_dtype_stays_unknown(self):
        payload = {"num_hidden_layers": 4, "num_attention_heads": 4, "hidden_size": 256}
        with tempfile.TemporaryDirectory() as tmp:
            shape = load_model_shape(write_config(tmp, payload))
        self.assertEqual(shape.dtype, "unknown")

    def test_weights_measured_from_real_safetensors_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            shape = load_model_shape(
                write_config(
                    tmp,
                    QWEN25_AWQ,
                    {"model-00001-of-00002.safetensors": 1000,
                     "model-00002-of-00002.safetensors": 2345},
                )
            )
        self.assertEqual(shape.weights_bytes, 3345)

    def test_weights_unknown_when_no_safetensors_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            shape = load_model_shape(write_config(tmp, QWEN25_AWQ))
        self.assertIsNone(shape.weights_bytes)

    def test_sliding_window_is_carried_through(self):
        payload = dict(QWEN25_AWQ, sliding_window=4096, use_sliding_window=True)
        with tempfile.TemporaryDirectory() as tmp:
            shape = load_model_shape(write_config(tmp, payload))
        self.assertEqual(shape.sliding_window, 4096)

    def test_missing_config_names_the_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ConfigError) as ctx:
                load_model_shape(tmp)
            self.assertIn(tmp, str(ctx.exception))

    def test_broken_json_names_the_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "config.json")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("{not json")
            with self.assertRaises(ConfigError) as ctx:
                load_model_shape(tmp)
            self.assertIn(path, str(ctx.exception))

    def test_config_missing_layer_count_is_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ConfigError) as ctx:
                load_model_shape(write_config(tmp, {"hidden_size": 1024}))
            self.assertIn("num_hidden_layers", str(ctx.exception))

    def test_huggingface_cache_layout_yields_a_readable_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            hub = os.path.join(tmp, "models--Qwen--Qwen3-1.7B", "snapshots", "abc123")
            os.makedirs(hub)
            with open(os.path.join(hub, "config.json"), "w", encoding="utf-8") as fh:
                json.dump(QWEN25_AWQ, fh)
            shape = load_model_shape(hub)
        self.assertEqual(shape.name, "Qwen/Qwen3-1.7B")


if __name__ == "__main__":
    unittest.main()
