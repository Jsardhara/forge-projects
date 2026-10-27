"""KV-cache arithmetic tests: the numbers the whole tool stands on."""

import unittest

from kvpreflight.arith import (
    bytes_per_token,
    dtype_bytes,
    kv_heads_per_rank,
    pool_tokens,
    UnknownFact,
)
from kvpreflight.model import ModelShape


def qwen3_1_7b(**over):
    """Real shape of Qwen/Qwen3-1.7B: 28 layers, 8 KV heads, head_dim 128, bf16."""
    base = dict(
        name="Qwen3-1.7B",
        layers=28,
        kv_heads=8,
        attn_heads=16,
        head_dim=128,
        dtype="bfloat16",
        sliding_window=None,
        weights_bytes=None,
    )
    base.update(over)
    return ModelShape(**base)


class TestDtypeBytes(unittest.TestCase):
    def test_half_precisions_are_two_bytes(self):
        for name in ("float16", "fp16", "bfloat16", "bf16", "half"):
            self.assertEqual(dtype_bytes(name), 2, name)

    def test_float32_is_four_bytes(self):
        self.assertEqual(dtype_bytes("float32"), 4)

    def test_fp8_is_one_byte_because_that_halves_the_pool(self):
        for name in ("float8_e4m3fn", "fp8", "fp8_e4m3"):
            self.assertEqual(dtype_bytes(name), 1, name)

    def test_unknown_dtype_is_unknown_not_two(self):
        with self.assertRaises(UnknownFact):
            dtype_bytes("int4")


class TestBytesPerToken(unittest.TestCase):
    def test_real_qwen3_bytes_per_token(self):
        # 2 (K and V) * 28 layers * 8 kv heads * 128 head_dim * 2 bytes
        self.assertEqual(bytes_per_token(qwen3_1_7b(), tensor_parallel_size=1), 114688)

    def test_tensor_parallel_shards_the_kv_cache(self):
        self.assertEqual(bytes_per_token(qwen3_1_7b(), tensor_parallel_size=2), 57344)
        self.assertEqual(bytes_per_token(qwen3_1_7b(), tensor_parallel_size=4), 28672)

    def test_fp8_kv_cache_halves_it(self):
        self.assertEqual(
            bytes_per_token(qwen3_1_7b(dtype="bfloat16"), 1, kv_dtype="fp8"), 57344
        )

    def test_kv_dtype_auto_follows_model_dtype(self):
        self.assertEqual(bytes_per_token(qwen3_1_7b(), 1, kv_dtype="auto"), 114688)


class TestKvHeadsPerRank(unittest.TestCase):
    def test_divides_evenly(self):
        self.assertEqual(kv_heads_per_rank(8, 2), (4, None))
        self.assertEqual(kv_heads_per_rank(8, 4), (2, None))
        self.assertEqual(kv_heads_per_rank(4, 1), (4, None))

    def test_tp_larger_than_kv_heads_replicates_heads(self):
        heads, note = kv_heads_per_rank(8, 16)
        self.assertEqual(heads, 1)
        self.assertIsNotNone(note)
        self.assertIn("replicat", note)

    def test_uneven_split_is_flagged_not_silently_rounded(self):
        heads, note = kv_heads_per_rank(8, 3)
        self.assertEqual(heads, 3)
        self.assertIsNotNone(note)
        self.assertIn("divisible", note)


class TestPoolTokens(unittest.TestCase):
    def test_block_size_rounds_down_never_up(self):
        bpt = 114688
        budget = 1048575 * bpt  # one token short of 2**20
        self.assertEqual(pool_tokens(budget, block_size=16, bytes_per_token=bpt), 1048560)

    def test_exact_fit_is_exact(self):
        bpt = 114688
        self.assertEqual(
            pool_tokens(1048576 * bpt, block_size=16, bytes_per_token=bpt), 1048576
        )

    def test_zero_budget_yields_zero_tokens(self):
        self.assertEqual(pool_tokens(0, 16, 114688), 0)


if __name__ == "__main__":
    unittest.main()
