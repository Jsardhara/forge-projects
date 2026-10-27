"""Command line surface. Exit 0 PASS, 1 FAIL, 2 UNKNOWN/could-not-answer."""

import argparse
import json
import sys

from . import report as report_mod
from .model import ConfigError, load_model_shape

GIB = 1024 ** 3


class _Parser(argparse.ArgumentParser):
    """Argparse that reports usage errors as exit 2 through main(), not SystemExit."""

    def error(self, message):
        raise ValueError(message)


def build_parser():
    p = _Parser(prog="kvpreflight",
                description="Does the KV pool this configuration implies hold the "
                            "context length it advertises?")
    p.add_argument("--model", required=True,
                   help="model directory (or path to config.json)")
    p.add_argument("--max-model-len", required=True, type=int,
                   help="the context length the server advertises")
    p.add_argument("--tensor-parallel-size", type=int, default=1)
    p.add_argument("--gpu-memory-utilization", type=float, default=0.90)
    p.add_argument("--device-vram-gb", type=float, default=None,
                   help="VRAM per GPU in GiB (omit and the answer is UNKNOWN)")
    p.add_argument("--num-gpus", type=int, default=None,
                   help="defaults to --tensor-parallel-size")
    p.add_argument("--weights-gb", type=float, default=None,
                   help="override the measured weight footprint")
    p.add_argument("--overhead-gb", type=float, default=0.0,
                   help="activations/graphs/driver reserve to subtract")
    p.add_argument("--kv-cache-dtype", default="auto",
                   help="auto (model dtype), fp8, fp16, bf16")
    p.add_argument("--block-size", type=int, default=16)
    p.add_argument("--max-num-seqs", type=int, default=None,
                   help="advisory: how many full-context sequences you expect")
    p.add_argument("--json", action="store_true", help="machine-readable output")
    return p


def _inputs(args):
    return report_mod.Inputs(
        max_model_len=args.max_model_len,
        tensor_parallel_size=args.tensor_parallel_size,
        gpu_memory_utilization=args.gpu_memory_utilization,
        device_vram_bytes=None if args.device_vram_gb is None
        else int(args.device_vram_gb * GIB),
        num_gpus=args.num_gpus,
        weights_bytes=None if args.weights_gb is None
        else int(args.weights_gb * GIB),
        overhead_bytes=int(args.overhead_gb * GIB),
        kv_cache_dtype=args.kv_cache_dtype,
        block_size=args.block_size,
        max_num_seqs=args.max_num_seqs,
    )


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        args = build_parser().parse_args(argv)
    except ValueError as exc:
        print("UNKNOWN: bad invocation: %s" % exc)
        print("  (nothing was checked; usage errors are exit 2, never 0)")
        return 2

    try:
        shape = load_model_shape(args.model)
    except ConfigError as exc:
        print("UNKNOWN: cannot read the model configuration: %s" % exc)
        return 2

    try:
        result = report_mod.evaluate(shape, _inputs(args))
    except ValueError as exc:
        print("UNKNOWN: %s" % exc)
        return 2

    if args.json:
        print(json.dumps(report_mod.to_dict(result), indent=2, sort_keys=True))
    else:
        print(report_mod.render_text(result))
    return result.exit_code


if __name__ == "__main__":
    sys.exit(main())
