# hostfit

**Will this workload fit in this host's RAM — right now, with these processes running?**

Read-only, stdlib only, no network, no root. It measures the kernel's own numbers
(`/proc/meminfo`, `/proc/<pid>/status`, `statvfs /dev/shm`) against a declared peak RSS and
returns a five-way verdict, the reclaim arithmetic, and the shortest list of processes whose
RSS would close the gap.

## Why this exists

Published requirements are about *a* machine, not *this* machine. `llama-modchip` states that
DeepSeek-V4-Flash 284B peaks at **57.61 GiB VmRSS** and "fits in 62.5 GiB usable Linux RAM".
On 2026-11-09 this rig had **89.7 GiB total** but **62.8 GiB available** — the difference held
by a 18.1 GiB python process and a resident 4.9 GiB `llama-server`. `MemTotal` says yes;
`MemAvailable` says "yes, with 5.2 GiB of slack instead of the 5.8 GiB headroom you asked for".
That difference is the whole tool.

## What it measures

| Signal | Source | Failure mode |
|---|---|---|
| available / total memory | `MemAvailable`, `MemTotal` in `/proc/meminfo` | field missing → `UNMEASURED`, exit 2 |
| swap | `SwapFree` | reported, **never added to capacity** |
| RSS holders | `/proc/<pid>/status` `VmRSS` | unreadable process counted, scan says how many |
| `/dev/shm` | `statvfs` | short → `BLOCKED_NOW` when the requirement asks for shm |

## Verdicts and exit codes

| State | Meaning | Exit |
|---|---|---|
| `FIT` | `available - peak >= headroom%` of the peak | 0 |
| `TIGHT` | fits, but margin is inside the headroom — no room for another process | 1 |
| `BLOCKED_NOW` | does not fit as loaded; reclaim number + `stop to fit` list printed | 1 |
| `IMPOSSIBLE` | peak exceeds physical `MemTotal` — stopping everything is not enough | 1 |
| `UNMEASURED` | meminfo unreadable / field missing — never read as a pass | 2 |

Exit 2 outranks exit 1: unmeasurable is not clean.

## Usage

```bash
cd 2026-11-09-hostfit
PYTHONPATH=src python3 -m hostfit --peak-gib 40
PYTHONPATH=src python3 -m hostfit --requirement examples/llama-modchip-dsv4-284b.json --top 5
PYTHONPATH=src python3 -m hostfit --peak-gib 70 --json
```

Requirement file (`peak_gib` required, the rest optional):

```json
{"name": "llama-modchip-dsv4-284b", "peak_gib": 57.61, "shm_gib": 0, "headroom_pct": 10}
```

## Measured on this host (2026-11-09T06:2xZ, real `/proc`)

```
hostfit: llama-modchip-deepseek-v4-flash-284b
  state            : TIGHT
  available / total: 62.82 / 89.71 GiB
  required         : 57.61 GiB (headroom 10.0%)
  - margin 5.2 GiB < 5.8 GiB headroom: works, but with no room for another process
  top RSS holders: python 18.138 GiB · llama-server 4.89 GiB · hermes 1.203 GiB
EXIT=1
```

```
hostfit: llama-modchip-nemotron-30b-a3b-256k   state: FIT (margin 47.8 GiB)   EXIT=0
hostfit --peak-gib 70                          state: BLOCKED_NOW, short 7.1 GiB,
                                               stop to fit: python            EXIT=1
hostfit --peak-gib 5 --meminfo /nonexistent     state: UNMEASURED              EXIT=2
```

## What it is not

It does not predict throughput (that is `llama-modchip`'s own readiness audit) and it does not
compute KV-cache size from a model config (`kvpreflight`, 2026-10-27, does that). It answers
one question: given a peak RSS someone else measured, does it fit here today, and who is in
the way.

## Tests

```bash
cd 2026-11-09-hostfit && PYTHONPATH=src python3 -m unittest discover -s tests
# 32 tests, OK
```

Statement coverage via stdlib `trace`: verdict 98.5% · procs 96.6% · cli 95.3% · meminfo 90.7%.
