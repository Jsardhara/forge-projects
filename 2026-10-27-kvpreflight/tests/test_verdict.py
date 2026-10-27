"""The verdict layer: PASS / FAIL / UNKNOWN and the reasons behind each."""

import unittest

from kvpreflight.model import ModelShape
from kvpreflight.report import Inputs, evaluate

GIB = 1024 ** 3


def qwen3():
    # 28 layers x 8 kv heads x 128 head_dim x 2 bytes x 2 (K+V) = 114,688 B/token
    return ModelShape(
        name="Qwen3-1.7B",
        layers=28,
        kv_heads=8,
        attn_heads=16,
        head_dim=128,
        dtype="bfloat16",
        sliding_window=None,
        weights_bytes=4 * GIB,
    )


def inputs(**over):
    base = dict(
        max_model_len=40960,
        tensor_parallel_size=1,
        gpu_memory_utilization=0.90,
        device_vram_bytes=24 * GIB,
        num_gpus=1,
        weights_bytes=4 * GIB,
        overhead_bytes=2 * GIB,
        kv_cache_dtype="auto",
        block_size=16,
        max_num_seqs=None,
    )
    base.update(over)
    return Inputs(**base)


class TestPassFail(unittest.TestCase):
    def test_generous_pool_passes(self):
        report = evaluate(qwen3(), inputs())
        self.assertEqual(report.verdict, "PASS")
        self.assertEqual(report.exit_code, 0)
        self.assertGreaterEqual(report.pool_tokens, 40960)

    def test_pool_below_context_fails_with_the_numbers(self):
        # Shrink VRAM so the budget holds far less than the advertised context.
        report = evaluate(qwen3(), inputs(device_vram_bytes=6 * GIB))
        self.assertEqual(report.verdict, "FAIL")
        self.assertEqual(report.exit_code, 1)
        self.assertLess(report.pool_tokens, report.max_model_len)
        self.assertIn("short", report.headline.lower())

    def test_exact_fit_passes_at_the_boundary(self):
        # 100 blocks of 16 tokens is exactly 1600 tokens; nothing may be rounded away.
        bpt = 114688
        budget = 100 * 16 * bpt
        report = evaluate(
            qwen3(),
            inputs(
                max_model_len=1600,
                device_vram_bytes=budget + 6 * GIB,
                gpu_memory_utilization=1.0,
                weights_bytes=4 * GIB,
                overhead_bytes=2 * GIB,
            ),
        )
        self.assertEqual(report.pool_tokens, 1600)
        self.assertEqual(report.verdict, "PASS")

    def test_one_token_short_fails(self):
        bpt = 114688
        budget = 99 * 16 * bpt
        report = evaluate(
            qwen3(),
            inputs(
                max_model_len=1600,
                device_vram_bytes=budget + 6 * GIB,
                gpu_memory_utilization=1.0,
                weights_bytes=4 * GIB,
                overhead_bytes=2 * GIB,
            ),
        )
        self.assertEqual(report.pool_tokens, 1584)
        self.assertEqual(report.verdict, "FAIL")


class TestUnknownIsASecondClassCitizen(unittest.TestCase):
    def test_no_device_vram_is_unknown_not_pass(self):
        report = evaluate(qwen3(), inputs(device_vram_bytes=None))
        self.assertEqual(report.verdict, "UNKNOWN")
        self.assertEqual(report.exit_code, 2)
        self.assertIn("device VRAM", report.headline)

    def test_no_weights_is_unknown(self):
        shape = qwen3()
        shape.weights_bytes = None
        report = evaluate(shape, inputs(weights_bytes=None))
        self.assertEqual(report.verdict, "UNKNOWN")
        self.assertIn("weight", report.headline.lower())

    def test_unknown_dtype_is_unknown(self):
        shape = qwen3()
        shape.dtype = "int4"
        report = evaluate(shape, inputs(kv_cache_dtype="auto"))
        self.assertEqual(report.verdict, "UNKNOWN")
        self.assertEqual(report.exit_code, 2)

    def test_budget_eaten_by_weights_is_a_fail_not_a_crash(self):
        report = evaluate(qwen3(), inputs(device_vram_bytes=5 * GIB))
        self.assertEqual(report.verdict, "FAIL")
        self.assertEqual(report.pool_tokens, 0)

    def test_unknown_reports_the_number_it_could_not_establish(self):
        report = evaluate(qwen3(), inputs(device_vram_bytes=None))
        self.assertTrue(any("device_vram" in note for note in report.notes))


class TestAdvisories(unittest.TestCase):
    def test_concurrency_contention_is_noted_but_does_not_fail(self):
        report = evaluate(qwen3(), inputs(max_num_seqs=8))
        self.assertEqual(report.verdict, "PASS")
        self.assertTrue(any("concurren" in note.lower() for note in report.notes))

    def test_tp_replication_is_noted(self):
        report = evaluate(qwen3(), inputs(tensor_parallel_size=16, num_gpus=16))
        self.assertTrue(any("replicat" in note.lower() for note in report.notes))

    def test_uneven_kv_head_split_is_noted(self):
        report = evaluate(qwen3(), inputs(tensor_parallel_size=3, num_gpus=3))
        self.assertTrue(any("divisible" in note.lower() for note in report.notes))

    def test_sliding_window_is_noted(self):
        shape = qwen3()
        shape.sliding_window = 4096
        report = evaluate(shape, inputs())
        self.assertTrue(any("sliding" in note.lower() for note in report.notes))

    def test_gpu_memory_utilization_is_reported_as_a_ceiling(self):
        report = evaluate(qwen3(), inputs())
        self.assertTrue(any("upper bound" in note.lower() for note in report.notes))


if __name__ == "__main__":
    unittest.main()
