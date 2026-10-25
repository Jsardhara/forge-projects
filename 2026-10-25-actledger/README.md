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

Chain break codes: `PARSE-ERROR`, `SEQ-GAP`, `PREV-MISMATCH`, `HASH-MISMATCH`,
`HEAD-MISMATCH`, and in bundles `FORMAT-MISMATCH`, `COUNT-MISMATCH`.

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

## Tests

```sh
PYTHONPATH=src python3 -m unittest discover -s tests
```

101 tests, no third-party test runner required.

## Layout

```
src/actledger/
  models.py    frozen record / entry / finding types, severity-dominant verdict
  chain.py     canonical JSON, hashing, chain verification
  ledger.py    file-backed append-only ledger + committed head
  audit.py     responsibility report (the differentiator)
  export.py    self-contained bundles
  sources.py   adapters from an existing runtime's own records
  cli.py       record / verify / audit / export / verify-bundle / tail
scripts/from_hermes_kanban.py
tests/
```
