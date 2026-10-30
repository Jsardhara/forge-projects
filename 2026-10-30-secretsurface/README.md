# secretsurface

**Where key material actually lives — by class, with a revoke list, without ever
printing the secret.**

`grep .env` answers "is it in `.env`". That is not the question. The question is
*where is it*, and on a multi-profile agent host the honest answer is usually
"in an activity log, a curator backup blob, or a `.env.bak` you forgot you made".

`secretsurface` walks a root list, finds high-precision credential shapes,
classifies **which kind of store** each hit lives in, measures blast-radius
signals, and emits the paths to rotate from. It is read-only and offline.

## Why not gitleaks / trufflehog

They answer "find secrets" and they answer it well, for repositories and commit
history. They report a location, not a *store class*, and they default to
annotating the matched value. This tool answers a different question — "which of
these is a live `.env`, which is a superseded backup, which is an append-only
log, which is a doc example" — and it never has the value to leak.

## Usage

Standard library only. No install step.

```bash
cd 2026-10-30-secretsurface
PYTHONPATH=src python3 -m secretsurface                 # default roots
PYTHONPATH=src python3 -m secretsurface ~/.hermes/profiles
PYTHONPATH=src python3 -m secretsurface --json
PYTHONPATH=src python3 -m secretsurface --revoke-list    # paths only
PYTHONPATH=src python3 -m secretsurface --quiet          # silent when clean
```

Default roots: `~/.hermes/profiles`, `~/.hermes/skills`, `~/code/jarmes`.

### Exit codes

| Code | Meaning |
|---|---|
| 0 | clean — every file was read and no credential shape found |
| 1 | findings |
| 2 | **unmeasurable** — zero files read, or a root could not be opened |

Exit 2 is not a failure of nerve. It means *nothing was proven*, which is
different from clean. Same 3-way contract as `kvpreflight` and `tsattest`, so all
three roll into one fleet report.

## What it reports

```
/home/jyot/.hermes/profiles/forge/.env.bak.si09-20260911:545  generic-sk-key  env-backup  fp=1209 len=73  [superseded-key-may-still-validate, duplicate-of-live-env]
```

Path, line, pattern id, store class, and a **4-character sha256 fingerprint** —
enough to prove two sightings are the same value, useless to anyone who
intercepts the report.

### Store classes

| Class | Meaning |
|---|---|
| `env` | live environment file (`.env`, `.env.local`) |
| `env-backup` | a superseded env file (`.env.bak.*`, `.env.old`) — rotation residue |
| `log-leak` | append-only log or `.jsonl` activity trail |
| `backup-blob` | curator snapshot, `backups/` dir, `~`/`.bak` copy |
| `doc-fixture` | documentation, test fixture, skill example — *probably* benign |
| `unknown` | **unclassified, and therefore not safe** |

`unknown` is a real answer, not a failure. An unclassified hit is
indistinguishable from a live credential until a human reads it, so it is never
silently bucketed as safe.

### Blast-radius signals

| Signal | Meaning |
|---|---|
| `world-readable` | file mode grants read to every user on the box |
| `in-git-worktree` | a `.git` sits above it — it can be committed as-is |
| `superseded-key-may-still-validate` | a backup: rotation did not necessarily reach it |
| `duplicate-of-live-env` | this backup's fingerprint **equals a live `.env` value** |
| `copied-or-shipped` | a log: tailed, shipped, pasted into issues |
| `unclassified-store` | nobody decided what this file is |

`duplicate-of-live-env` is the load-bearing one. A key in a backup is mild. A
backup holding *the live value* means rotating `.env` alone leaves a working
copy of the same key on disk — which is how a finished-looking rotation stays
unfinished.

## Design rules

- **Never emit the value.** Only path, line, pattern id, class, signals and a
  4-char fingerprint. A scanner that echoes the key has created a second leak,
  in the terminal scrollback of an automated job.
- **Precision over recall.** Six high-precision shapes only. Every skip is
  counted and printed: *a skip that is not counted is a silent hole*.
- **Dot-directories are scanned.** The leak lives in `.curator_backups/`; a
  walker that hides dotdirs reports clean while the key sits there.
- **A PEM header alone is not a key.** Documentation writes the marker with no
  body. Requiring a base64 body removed 34 false findings on real data.

## What it does not do

- **Commit history** — `.git` is skipped and reported. Use a history scanner.
- **Rotation / deletion** — operator-only (T4). This tool emits the evidence and
  the revoke list; deleting another profile's credentials is how you take down a
  fleet.
- **Decrypting** — a key inside a password manager vault or an encrypted blob is
  out of scope.

## Verification

105 unit tests (`PYTHONPATH=src python3 -m unittest discover -s tests`), 96%
statement coverage across `src/`.

Measured against the live host (2026-10-30): 9,643 files scanned, 50,599 skipped
and reported, **17 findings in 17 files**. First real outing corrected its own
source premise — the "log leak" and "curator blob" hits that motivated the build
turned out to be prose matching `sk-` inside "risk-"/"disk-" and the published
AWS documentation example key. The tool filters both. What survives is a real
one: eight profiles' `.env.bak.si09-20260911` files carry a byte-identical copy
of the live `.env` key.
