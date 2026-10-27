# kvpreflight

**Does the KV pool this configuration implies actually hold the context length it
advertises?** Offline, stdlib-only, one number, three possible answers.

```bash
PYTHONPATH=src python3 -m kvpreflight \
  --model /path/to/hf-model-dir \
  --max-model-len 1048576 \
  --device-vram-gb 24 \
  --gpu-memory-utilization 0.90 \
  --overhead-gb 2
```

```
FAIL: KV pool holds 269,840 tokens, 778,736 short of the advertised 1,048,576
(74.3% of the context does not exist; 57,344 bytes/token, 14.41 GiB budget)
  model:                       Qwen/Qwen2.5-7B-Instruct-AWQ
  layers x kv_heads x head_dim: 28 x 4 x 128
  kv heads per rank (tp=1):    4
  bytes per token:             57344
  kv budget:                   14.41 GiB
  pool tokens:                 269,840
  advertised context:          1,048,576
```

## Why this exists

Cloudflare deployed GLM-5.3 advertising a 1,048,576-token context on a prefill KV pool
that held 681,280 tokens. Their post-mortem states the mismatch was known before launch:
they expected the engine to error on an over-length prompt. It did not — it prefilled a
one-token placeholder and the decode node attended over stale cache pages from other
tenants. 155 responses leaked cross-tenant data.

The remediation post names the durable problem: *"any change to quantization, tensor
parallelism, CUDA graph sizes, or a future model version changes the pool size in a way
that's easy to miss."* Nothing in CI checks `kv_pool_tokens >= max_model_len`. This tool
does, offline, from the model's own `config.json`.

## What it computes

```
bytes/token = 2 (K and V) x kv_heads_per_rank x head_dim x elem_bytes x num_layers
kv_budget   = gpu_memory_utilization x device_vram x num_gpus
              - weights - overhead
pool_tokens = floor(kv_budget / (block_size x bytes/token)) x block_size
verdict     = PASS if pool_tokens >= max_model_len else FAIL
```

- **Weights are measured, not guessed.** The safetensors index `total_size` (or the real
  file sizes) of the model directory. AWQ/GPTQ checkpoints therefore get their true
  footprint, not `params x dtype`.
- **`head_dim` is derived** from `hidden_size / num_attention_heads` when the config omits
  it, as real Qwen2.5 configs do.
- **Tensor parallelism shards the cache**, and both replication (`tp > kv_heads`) and an
  uneven split are reported as notes.
- **`--kv-cache-dtype fp8`** halves the per-token cost.
- **Block rounding is always down.** Half a block holds zero tokens.

## Exit codes (fail-closed)

| code | meaning |
|---|---|
| 0 | `PASS` — the pool holds the advertised context |
| 1 | `FAIL` — it does not; the shortfall in tokens and percent is printed |
| 2 | `UNKNOWN` — a number required for the verdict could not be established |

`UNKNOWN` is a first-class answer, not an error path. A preflight that answers PASS from
a number it could not establish would reproduce the incident it exists to prevent. What
it cannot establish it names: device VRAM (`--device-vram-gb`), the weight footprint, an
unknown element type, an unreadable config path.

## Options

| flag | default | meaning |
|---|---|---|
| `--model` | required | model directory, or a path to `config.json` |
| `--max-model-len` | required | the context length the server advertises |
| `--tensor-parallel-size` | 1 | TP degree; shards KV heads per rank |
| `--gpu-memory-utilization` | 0.90 | the engine's memory ceiling request |
| `--device-vram-gb` | none | VRAM per GPU in GiB; omit and the verdict is UNKNOWN |
| `--num-gpus` | = TP size | number of GPUs in the deployment |
| `--weights-gb` | measured | override the measured weight footprint |
| `--overhead-gb` | 0 | activations / CUDA graphs / driver reserve to subtract |
| `--kv-cache-dtype` | auto | `auto` (model dtype), `fp8`, `fp16`, `bf16` |
| `--block-size` | 16 | KV block size for rounding |
| `--max-num-seqs` | none | advisory: check headroom for N full-context sequences |
| `--json` | off | machine-readable report (verdict, exit_code, every number, notes) |

## Verification against a real engine

The arithmetic was calibrated against a **real vLLM 0.29 run on this host**
(`Qwen/Qwen3-1.7B`, `--max-model-len 2048`, `--gpu-memory-utilization 0.28`,
`tensor_parallel_size 1`, bf16). That run's log records the engine's own measurement:

```
GPU KV cache size: 20,432 tokens, Maximum concurrency for 2,048 tokens per request: 9.98x
Actual usage is 3.61 GiB for consumed memory (weights + non-torch), 0.8 GiB for peak
activation, and 0.41 GiB for CUDAGraph memory.
```

Given that run's real device (23.56 GiB), utilization (0.28), weights+non-torch (3.61)
and peak activation (0.8):

```
$ PYTHONPATH=src python3 -m kvpreflight --model <Qwen3-1.7B> --max-model-len 2048 \
    --gpu-memory-utilization 0.28 --device-vram-gb 23.56 \
    --weights-gb 3.61 --overhead-gb 0.8
PASS: KV pool holds 20,464 tokens >= advertised context 2,048 (2.19 GiB budget)
```

20,464 predicted vs 20,432 measured: **+0.16%**, which is the block rounding plus the
log's two-decimal GiB. The engine's own bytes-per-token follows from its numbers:
2.18 GiB / 20,432 tokens = 114,619 B, against the tool's 114,688 B (**0.06%**).

Second real input: `Qwen/Qwen2.5-7B-Instruct-AWQ` (no `head_dim` in config, 4-bit
checkpoint) — tool derives `head_dim=128`, measures **5,570,747,392 bytes** of real
weights, and computes 57,344 B/token (56 KiB), the documented figure for a 7B GQA model.

## Limits, stated plainly

- `gpu_memory_utilization` is a **request**, not a measurement. The budget is an upper
  bound: activations, CUDA graphs and driver reservations are not modelled unless you
  pass `--overhead-gb`. Under-declaring the overhead is the way to turn a real FAIL into
  a false PASS — so the report says "upper bound" every time.
- The tool cannot see a pool the engine has already allocated. It answers what the
  configuration implies, not what a running server did.
- Attention variants that change KV geometry (MLA compression, per-layer KV head counts,
  hybrid linear attention) are not modelled. Such configs should be treated as out of
  scope rather than trusted.
- No `--device-vram-gb`, no talk to the GPU: this runs in CI on a laptop.

## Tests

```bash
cd 2026-10-27-kvpreflight
PYTHONPATH=src python3 -m unittest discover -s tests
```

48 tests, stdlib `unittest` only (pytest is not installed on the build host).
Line coverage measured with `python3 -m trace`: 100% on all six source modules
(arith 46, budget 6, cli 69, model 79, report 139, `__init__` 2 statements executed).

## Zero dependencies

Standard library only — `json`, `os`, `argparse`, `sys`. No torch, no transformers, no
GPU access, no network. It runs wherever Python 3.8+ runs.
