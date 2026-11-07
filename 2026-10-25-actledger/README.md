# actledger — an agent action evidence ledger

An append-only, hash-chained record of what an agent actually did, plus the one field a
normal log never has: **who was assigned to verify it**.

Zero dependencies. Standard library only. Runs on the machine that acted; verifies on a
machine that does not trust it.

## Why

On 2026-10-25 the eMudhra intermediate-certificate compromise surfaced publicly
([Mozilla Bug 2083449](https://bugzilla.mozilla.org/show_bug.cgi?id=2083449)): a CA key
that was literally the number `4` passed its audit. The signature checked out. Nobody was
assigned to own the check. The failure was organizational and no log format could express
it.

Agent fleets reproduce that. A runtime log — including the agent framework's own
`usage_audit.jsonl` — is mutable, host-local, and readable only by someone willing to
trust the process that wrote it. When a client, an insurer or a regulator asks "what did
the agent do, and who approved it", that log is not evidence.

This tool is the third leg of a line already in this repo:

| project | proves |
|---|---|
| `pubgate` | *what was published* matches what was built |
| `plugattest` | *what a plugin claims* matches what its code does, before install |
| **`actledger`** | *what an agent actually did at runtime*, in an artifact a third party can re-verify |

## What it guarantees, precisely

- **Edits are caught.** Every record's hash covers its sequence number, the previous
  hash and the canonical JSON of the record. Change one character of one field and
  `verify` names the sequence number.
- **Deletions and reordering are caught.** Sequence numbers and back-links are both
  checked, so a removed or moved record produces `SEQ-GAP` and `PREV-MISMATCH` at the
  exact position.
- **Truncation is caught.** The last hash is committed separately
  (`<ledger>.head.json`) and again inside every exported bundle, so lopping off the tail
  produces `HEAD-MISMATCH`.
- **Append refuses to launder damage.** Appending to a ledger whose file and committed
  head disagree raises instead of extending a damaged chain.
- **An exported bundle is self-contained.** No paths, no database handles, nothing that
  refers back to the runtime. `verify-bundle` needs the bundle and this tool's stdlib code.
- **A bundle proves what it claims.** Since 2026-11-07 it carries each measured digest's
  derivation and the posture the records earned at export time, and `verify-bundle`
  recomputes both. A binding edited inside the artifact is `BINDING-MISMATCH`; a declared
  posture the records do not earn is `AUDIT-DIVERGES`; a bundle carrying no bindings is
  `BINDINGS-ABSENT`, which exits 2 — *not checkable* is never reported as *clean*.

### What it does *not* protect against

Stated plainly, because a security tool that oversells is worse than none:

- **No signing key.** The chain is tamper-*evident*, not tamper-proof. Someone with write
  access to both the ledger *and* the head file can rewrite history and recompute every
  hash. Detection then depends on the head hash having been pinned somewhere else — in a
  published bundle, a ticket, a customer's copy. Do that.
- **It cannot tell you an action was wise.** It records that an action happened, who was
  named to check it, and who approved it. Judgement stays with the named humans.
- **Fields the source never recorded stay empty** (see the kanban adapter) and show up as
  findings. They are never guessed into place.

## Install

Nothing to install. Python 3.8+ and the source tree:

```sh
cd 2026-10-25-actledger
PYTHONPATH=src python3 -m actledger --help
```

## Use

Record one action:

```sh
PYTHONPATH=src python3 -m actledger record \
  --ledger actions.jsonl \
  --agent forge --tool file.write --outcome ok \
  --model deepseek/deepseek-v4.1 --model-digest sha256:9f2c... \
  --policy pol-2026-10-25 \
  --args-text "--force rebuild" \
  --data /srv/site/index.html \
  --verifier sentinel \
  --approved-by jyot --approved-at 2026-10-25T06:00:00Z
```

Facts recorded per action: agent id, model id, weights digest, policy version, tool,
arguments **hash** (never the arguments themselves), data touched, the assigned verifier,
human approval (who + when), outcome, timestamp, sequence number, previous hash, hash.

Verify, audit, export, re-verify elsewhere:

```sh
PYTHONPATH=src python3 -m actledger verify --ledger actions.jsonl
PYTHONPATH=src python3 -m actledger audit  --ledger actions.jsonl --fail-on warn
PYTHONPATH=src python3 -m actledger export --ledger actions.jsonl --out audit.bundle.json

# on the auditor's machine, with no access to the runtime:
python3 -m actledger verify-bundle audit.bundle.json
```

Exit codes, so this drops straight into CI:

| code | meaning |
|---|---|
| 0 | clean: chain verifies and the audit is under `--fail-on` |
| 1 | findings, or a chain that does not verify |
| 2 | usage error, missing file, unreadable input |

### Seeding from an existing fleet

```sh
PYTHONPATH=src python3 scripts/from_hermes_kanban.py \
  --db ~/.hermes/kanban.db --out actions.jsonl
```

One record per `task_runs` row. Fields the source never recorded (named verifier, policy
version, weights digest) are left empty on purpose so the audit counts them.

## Audit codes

Verdict is the **worst single finding**, never a sum — nine warnings do not add up to a
flag, and one flag is never diluted by a pile of passes.

| code | severity | meaning |
|---|---|---|
| `AAL-001` | FLAG | action has no named verifier — nobody was assigned to check it |
| `AAL-002` | FLAG | consequential action (write/exec/publish/send/trade/...) with no recorded human approval |
| `AAL-003` | WARN | the acting agent verified its own action |
| `AAL-004` | WARN | action cannot be tied to a model id + weights digest |
| `AAL-005` | WARN | action carries no policy version |
| `AAL-006` | PASS | every action names an assigned verifier |
| `AAL-007` | WARN | a digest is declared but **no tool measured it** — `MODEL-DIGEST-UNMEASURED` |

Chain break codes: `PARSE-ERROR`, `SEQ-GAP`, `PREV-MISMATCH`, `HASH-MISMATCH`,
`HEAD-MISMATCH`, and in bundles `FORMAT-MISMATCH`, `COUNT-MISMATCH`.

Bundle-provenance codes (2026-11-07) — these are what `verify-bundle` adds on top of the
chain, judged from the artifact alone:

| code | severity | meaning |
|---|---|---|
| `BINDING-MISMATCH` | FLAG | the bundle's binding names a different digest than its record, is malformed, or carries a fingerprint that is not a sha256 — the binding set lives outside the hash chain, so this is where tampering is caught |
| `BINDING-ORPHAN` | FLAG | the bundle binds a seq that is not a row carrying a model digest |
| `BINDING-DUPLICATE` | FLAG | one seq bound twice |
| `AUDIT-DIVERGES` | FLAG | the declared posture is not the posture these records earn |
| `BINDING-UNMEASURABLE` | WARN | a tagged digest with no binding, or a binding with no recorded fingerprint |
| `AUDIT-ABSENT` | WARN | the bundle declares no posture, so there is nothing to compare |
| `BINDINGS-ABSENT` | WARN | the artifact carries no bindings at all (format v1, or `--no-provenance`) — exits 2, not clean |
| `MANIFEST-NOT-BUNDLED` | INFO | fingerprints travelled but the manifest is not in the bundle, so they were not re-measured here |


## Binding a *measured* weights digest (2026-11-05)

`--model-digest` is a string you type, and `audit` used to accept any non-empty one. That
made the ledger's model-identity axis unfalsifiable: `abcdef` passed exactly as well as
the digest of the wrong model. The measurement side already exists in this repo —
`wsaudit` (2026-11-04) hashes the weights themselves. This is the other half:

```sh
# 1. measure the weights (wsaudit, 2026-11-04)
cd ../2026-11-04-wsaudit
PYTHONPATH=src python3 -m wsaudit hash /models/model.safetensors \
  --manifest-out /tmp/model.manifest.json

# 2. record with the manifest, not with a typed string
cd ../2026-10-25-actledger
PYTHONPATH=src python3 -m actledger record --ledger actions.jsonl \
  --agent forge --tool model.run --outcome ok --verifier sentinel --policy pol-7 \
  --model cross-encoder/ms-marco-MiniLM-L-6-v2 \
  --model-manifest /tmp/model.manifest.json
```

What `--model-manifest` does, in order, before anything is written:

1. shape-checks the manifest (tool, format, 64-hex digests, integer shapes);
2. **recomputes** the canonical digest from the manifest's own tensor list — the value in
   the record is derived here, not copied;
3. refuses a manifest that disagrees with itself, is header-only (`partial`), or declares
   no tensors;
4. refuses to record at all if a `--model-digest` was also supplied and it disagrees —
   exit `2`, nothing written. Preferring one silently is how a transcription launders
   itself into a measured-looking row.

The digest is stored as `ws1:<sha256>`, and one line per bound record is appended to
`<ledger>.manifests.jsonl`. It lives beside the ledger rather than inside it because the
record's field set is hashed into the chain — a new key would invalidate every ledger
written before today.

`audit` reads that file. A row is *measured* only when a binding line names the same
digest for that sequence number; the `ws1:` prefix alone proves nothing, because anyone
can type it. Everything else becomes `AAL-007 MODEL-DIGEST-UNMEASURED`.

The auditor's other direction — *what ran on these weights?*:

```sh
PYTHONPATH=src python3 -m actledger verify-binding \
  --ledger actions.jsonl --manifest /tmp/model.manifest.json [--json]
```

Exit `0` = at least one action is bound to this manifest's digest, `1` = none is,
`2` = could not measure. The two tools divide the work: `wsaudit hash <file> --manifest
<M>` proves the bytes on disk still match the manifest (exit `1` on a substituted
weight); `actledger` proves which actions are bound to that manifest.

## Verifying the manifest itself (2026-11-06)

A binding line records `format`, `tensor_count`, `manifest_sha256` and the manifest path.
Until today nothing read those four fields back: `audit` only asked whether a binding named
the same digest, so a MEASURED row carried provenance claims whose truth was never
checked. Edit the manifest after binding and the row still read MEASURED.

```sh
PYTHONPATH=src python3 -m actledger audit --ledger actions.jsonl --verify-manifest
```

For every MEASURED row it re-opens the recorded manifest, recomputes its canonical
sha256, and compares it with the fingerprint written at binding time. Three states —
never two:

| state | code | severity | meaning |
|---|---|---|---|
| pass | — | — | the manifest is still the file that produced this digest |
| changed | `MANIFEST-SHA-MISMATCH` | FLAG | edited after the digest was bound |
| unmeasurable | `MANIFEST-UNMEASURABLE` | WARN | gone, unreadable, or bound before fingerprints existed |

`MANIFEST-UNMEASURABLE` is not a pass. "Could not check" and "checked and fine" are
different answers, and the tool says which one it gave you. At the default `--fail-on FLAG`
an unmeasurable row is reported but does not fail the run; `--fail-on WARN` makes a
provenance gap fatal, which is what a CI gate over model lineage wants.

Portability: the binding records `manifest_basename` as well as the abspath. A ledger
copied to another machine with its manifest beside it still verifies — by name — and the
report says which resolution it used (`resolved_by: "path"` or `"basename"`). Resolution
never searches beyond the ledger's own directory: a same-named file somewhere else is not
the same measurement.

## The bundle proves the two legs it exists to carry (2026-11-07)

`export.py` says a bundle is "the artifact you hand to someone outside the machine…
Verification needs this tool's stdlib code and the bundle. That is the whole trust base."
For immutability that was true. For **responsibility** and **provenance** it was not: the
bundle carried `ws1:` digests and `verifier` columns with none of the verdicts that judge
them, so a receiver outside the machine could prove the records were not altered and
could not prove a single digest had been derived rather than typed.

Format `actledger-bundle/2` carries the bindings and the posture computed at export time.
`verify-bundle` now recomputes both from the artifact's own contents:

```sh
PYTHONPATH=src python3 -m actledger export --ledger actions.jsonl --out audit.bundle.json
PYTHONPATH=src python3 -m actledger verify-bundle audit.bundle.json
```

```
OK: 2 record(s) verified, head 347ac79df40294d5
  MANIFEST-NOT-BUNDLED seq=-1 manifest fingerprints travelled with the artifact but were
    not re-measured here: the manifest is not in the bundle. Re-measure it with
    'audit --verify-manifest' if you were handed the file
BINDINGS-PRESENT 2 binding(s) carried | 2 corroborated | 0 mismatched | 0 not checkable
audit: PASS declared, PASS earned by these records
state: PASS
```

Exit codes mirror `provenance`: `0` pass, `1` mismatch, `2` could not check. The binding
set lives **outside** the hash chain, so the artifact is the only place a rewritten binding
can be caught — that is why an edited binding is a FLAG rather than a warning.

`--no-provenance` writes a deliberately chain-only bundle. It records
`"provenance": "absent"` and a null binding list **in the file**, and verifies as
`BINDINGS-ABSENT` (exit 2) instead of silently looking clean. A v1 bundle reads the same
way: *not checkable*, never *clean*.

The manifest fingerprint still cannot be re-measured from the bundle alone, because the
manifest is not in it. Rather than imply otherwise, the artifact names that gap
(`MANIFEST-NOT-BUNDLED`, INFO) and the fingerprint stays actionable for whoever is also
handed the file: `audit --verify-manifest`.

## Measured on real data, not fixtures

Run against this host's live Hermes kanban database (635 real agent runs):

```
imported 635 run(s) from /home/jyot/.hermes/kanban.db
chain: OK (635 records, head 2063197a2a557474)
responsibility: verdict FLAG | unverified 635/635 | independently verified 0
```

That is the thesis measured rather than asserted: the fleet's own runtime records **zero**
named verifiers for every action it has ever run, because the system has no concept of
one. Five tamper classes were then applied to copies of that real ledger — edited field,
deleted middle record, reordered pair, truncated tail, forged append — and every one was
detected at the right sequence number. The exported bundle verified from a directory
containing only the bundle.

2026-11-07, on the real weights: `wan2.2_vae.safetensors`, 1,409,400,960 bytes, measured by
`wsaudit` into a 45,216-byte manifest (digest `ws1:d8fd214326feb41e…`, fingerprint
`fb09bc1fa579f1fb…`). Two actions were recorded against it, exported, and then the ledger,
the sidecar **and the manifest** were moved out of the way — a directory containing only
`audit.bundle.json` verified: `state: PASS`, 2 bindings carried, 2 corroborated, exit 0.

Four adversarial probes on that same real bundle, each asserting its own mutation first:

| probe | exit | code |
|---|---|---|
| binding rewritten inside the bundle | 1 | `BINDING-MISMATCH` (+ collateral `AUDIT-DIVERGES`: the forged digest no longer has a binding) |
| declared posture the records do not earn | 1 | `AUDIT-DIVERGES` |
| bundle downgraded to format v1 | 2 | `BINDINGS-ABSENT` |
| `--no-provenance` export | 2 | `BINDINGS-ABSENT` |

The importance of the first row: bindings are not covered by the hash chain, so before this
change the only way to catch a rewritten binding was to notice it by eye.

## Tests

```sh
PYTHONPATH=src python3 -m unittest discover -s tests
```

200 tests, no third-party test runner required. `tests/data/minilm.manifest.json` is a
manifest produced by `wsaudit` over a real 90 MB safetensors file, so the digest
reimplementation in `manifest.py` is checked against wsaudit's own output on every run.

## Layout

```
src/actledger/
  models.py    frozen record / entry / finding types, severity-dominant verdict
  chain.py     canonical JSON, hashing, chain verification
  ledger.py    file-backed append-only ledger + committed head
  audit.py     responsibility report (the differentiator)
  manifest.py  wsaudit manifest -> recomputed digest -> binding sidecar
  provenance.py re-measure the manifest each bound digest came from
  bundleproof.py prove the bundle's two legs from the artifact alone
  export.py    self-contained bundles (format 2: entries + bindings + posture)
  sources.py   adapters from an existing runtime's own records
  cli.py       record / verify / audit / export / verify-bundle / tail / verify-binding
scripts/from_hermes_kanban.py
tests/
```
