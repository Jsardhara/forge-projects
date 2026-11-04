# wsaudit

Per-tensor digests for model weight files. Reads `.safetensors` and `.gguf`,
streams from disk, never loads tensors into memory, never writes to the model
directory, never touches the network, no keys, no dependencies.

```
$ wsaudit hash <model> [--manifest-out FILE] [--manifest FILE] [--json] [--header-only]
$ wsaudit diff <base> <other> [--lora-map] [--top N] [--json]
```

## Why

A file-level `sha256sum` tells you two files differ. It cannot tell you *what*
differs, cannot distinguish a metadata rewrite from a weights change, and cannot
answer "does this adapter patch layer 12's `q_proj`?". A model digest that is a
caller-supplied string (as in an action ledger) is a transcription, not
evidence. `wsaudit` measures the tensors themselves: one digest per tensor, a
canonical digest over all of them, and a diff that names the modules.

## Exit contract - fail closed

| code | meaning |
|---|---|
| `0` | measured, and clean (digest computed / manifest agrees / models identical) |
| `1` | measured, and disagreeing (manifest mismatch / models differ) |
| `2` | could not measure (unknown format, truncation, bad manifest, partial scan) |

`2` outranks everything. A file that cannot be parsed never reports clean, and
`--header-only` (which skips payload hashing and is marked `PARTIAL`) is refused
when a manifest is supplied.

## What it measures

* **safetensors** - `u64` header length, JSON table of contents, then byte
  ranges. Every tensor is bounds-checked against the file size and against
  `dtype x shape`, so a truncated or hand-edited header fails loudly instead of
  producing a plausible digest. A ZIP container (a PEFT adapter saved with
  `torch.save` under a `.safetensors` name) is named as such and refused -
  the tool never unpickles model data.
* **GGUF** - magic, version, KV block (all 13 value types, large arrays
  summarised instead of stored), tensor-info table, alignment from
  `general.alignment`, and tensor sizes derived from the ggml block table
  (`Q4_K` = 256 elements / 144 bytes, `Q6_K` = 256 / 210, ...).
* **Model digest** - sha256 over the sorted `(name, dtype, shape, tensor-sha256)`
  tuples, every field length-prefixed so two different tensor sets cannot
  collide on a concatenation boundary.
* **Diff** - per-tensor L2 and relative norm for float tensors (`F64/F32/F16/BF16`),
  `n/a` for quantised payloads (no dequantisation is guessed). Rows are ranked by
  magnitude. With `--lora-map`, `lora_A`/`lora_B` (PEFT) and
  `lora_down`/`lora_up` (kohya) tensors are reported against the module they
  patch, e.g. `model.layers.12.self_attn.q_proj (lora_A)`.

## Verified against real files, not only fixtures

78 unit tests, plus these runs on the rig's own corpus:

| input | result |
|---|---|
| `clip_l.safetensors` (235 MB, 196 tensors) | digest `fe2e5e8c...`; names/dtypes/shapes **identical** to the official `safetensors` 0.8.0 parser |
| `Qwen3.8-27B-Uncensored-draft-Q4_0.gguf` (1.6 GB, 18 tensors) | **18/18 per-tensor sha256 match `llama-gguf-hash`** (llama.cpp's own hasher) |
| `Qwen3.8-27B-Uncensored-Q4_K_M.gguf` (16 GB, 866 tensors) | header parsed in 0.21 s, no payload read |
| two LTX-2.3 LoRAs (2.6 GB + 7.1 GB) | 13.8 s; 3320 patched, 0 changed, 1659 removed |
| one byte flipped inside `clip_l` | `exit 1`, `verdict: mismatch`, the tampered tensor named |

## Standard library only

No `safetensors`, no `gguf`, no `torch` at runtime. `python3 -m wsaudit` works
from a bare interpreter.

```
cd 2026-11-04-wsaudit
PYTHONPATH=src python3 -m wsaudit hash /path/to/model.gguf
PYTHONPATH=src python3 -m unittest discover -s tests
```

## Known limits (stated, not worked around)

* L2 is skipped for quantised (GGUF `Q*`, `IQ*`) and for tensors over 256 MB -
  reported as `n/a` rather than approximated.
* One file per invocation; sharded models are digested shard by shard.
* A manifest is a plain JSON file; it records no signature. `wsaudit` proves
  *what the bytes are*, not *who produced them*.
