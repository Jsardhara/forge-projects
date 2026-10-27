"""CLI contract: exit 0 clean, 1 at/above threshold, 2 could not answer."""

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout

from kvpreflight.cli import main

CONFIG = {
    "num_hidden_layers": 28,
    "num_attention_heads": 16,
    "num_key_value_heads": 8,
    "head_dim": 128,
    "hidden_size": 2048,
    "torch_dtype": "bfloat16",
}


def model_dir(tmp, weights_size=None):
    with open(os.path.join(tmp, "config.json"), "w", encoding="utf-8") as fh:
        json.dump(CONFIG, fh)
    if weights_size:
        with open(os.path.join(tmp, "model.safetensors"), "wb") as fh:
            fh.write(b"\0" * weights_size)
    return tmp


def run(argv):
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = main(argv)
    return code, buf.getvalue()


class TestExitCodes(unittest.TestCase):
    def test_pass_exits_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            model_dir(tmp, weights_size=1024)
            code, out = run([
                "--model", tmp,
                "--max-model-len", "8192",
                "--device-vram-gb", "24",
                "--weights-gb", "4",
                "--overhead-gb", "2",
            ])
        self.assertEqual(code, 0)
        self.assertIn("PASS", out)

    def test_fail_exits_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            model_dir(tmp, weights_size=1024)
            code, out = run([
                "--model", tmp,
                "--max-model-len", "1048576",
                "--device-vram-gb", "24",
                "--weights-gb", "4",
                "--overhead-gb", "2",
            ])
        self.assertEqual(code, 1)
        self.assertIn("FAIL", out)

    def test_missing_vram_exits_two_and_does_not_guess(self):
        with tempfile.TemporaryDirectory() as tmp:
            model_dir(tmp, weights_size=1024)
            code, out = run(["--model", tmp, "--max-model-len", "8192",
                             "--weights-gb", "4"])
        self.assertEqual(code, 2)
        self.assertIn("UNKNOWN", out)

    def test_unreadable_model_path_exits_two_naming_the_path(self):
        code, out = run(["--model", "/nonexistent/model/dir", "--max-model-len", "8192",
                         "--device-vram-gb", "24", "--weights-gb", "4"])
        self.assertEqual(code, 2)
        self.assertIn("/nonexistent/model/dir", out)

    def test_missing_required_arg_exits_two(self):
        code, out = run(["--device-vram-gb", "24"])
        self.assertEqual(code, 2)
        self.assertIn("max-model-len", out)


class TestJsonOutput(unittest.TestCase):
    def test_json_carries_the_numbers(self):
        with tempfile.TemporaryDirectory() as tmp:
            model_dir(tmp, weights_size=1024)
            code, out = run([
                "--model", tmp,
                "--max-model-len", "8192",
                "--device-vram-gb", "24",
                "--weights-gb", "4",
                "--overhead-gb", "2",
                "--json",
            ])
        payload = json.loads(out)
        self.assertEqual(code, payload["exit_code"])
        self.assertEqual(payload["verdict"], "PASS")
        self.assertEqual(payload["bytes_per_token"], 114688)
        self.assertEqual(payload["max_model_len"], 8192)
        self.assertIn("pool_tokens", payload)
        self.assertIn("notes", payload)

    def test_json_on_unknown_still_parses(self):
        with tempfile.TemporaryDirectory() as tmp:
            model_dir(tmp, weights_size=1024)
            code, out = run(["--model", tmp, "--max-model-len", "8192",
                             "--weights-gb", "4", "--json"])
        payload = json.loads(out)
        self.assertEqual(code, 2)
        self.assertEqual(payload["verdict"], "UNKNOWN")
        self.assertIsNone(payload["pool_tokens"])


class TestTpScaling(unittest.TestCase):
    def test_more_gpus_means_more_pool(self):
        with tempfile.TemporaryDirectory() as tmp:
            model_dir(tmp, weights_size=1024)
            code1, out1 = run(["--model", tmp, "--max-model-len", "8192",
                               "--device-vram-gb", "24", "--weights-gb", "4",
                               "--overhead-gb", "2", "--json"])
            code2, out2 = run(["--model", tmp, "--max-model-len", "8192",
                               "--device-vram-gb", "24", "--weights-gb", "4",
                               "--overhead-gb", "2", "--tensor-parallel-size", "2",
                               "--json"])
        one, two = json.loads(out1), json.loads(out2)
        self.assertEqual(one["verdict"], "PASS")
        self.assertEqual(two["verdict"], "PASS")
        # Four times the KV budget at half the bytes/token = 8x the tokens.
        self.assertGreater(two["pool_tokens"], one["pool_tokens"])

    def test_num_gpus_defaults_to_tensor_parallel_size(self):
        with tempfile.TemporaryDirectory() as tmp:
            model_dir(tmp, weights_size=1024)
            code, out = run(["--model", tmp, "--max-model-len", "8192",
                             "--device-vram-gb", "24", "--weights-gb", "4",
                             "--overhead-gb", "2", "--tensor-parallel-size", "2",
                             "--json"])
        self.assertEqual(json.loads(out)["num_gpus"], 2)


if __name__ == "__main__":
    unittest.main()
