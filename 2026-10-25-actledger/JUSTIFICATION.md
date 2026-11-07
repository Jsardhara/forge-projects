# Project Justification — actledger (Agent Action Evidence Ledger)

## The problem

An audit of a machine doing work is only as good as its answer to one question: *who was
assigned to check this act, and can someone outside the machine re-verify it?* On
2026-10-25 the CA eMudhra case answered that question in the worst possible way — an
intermediate certificate key that was literally the number `4` passed its own audit
(Mozilla Bug 2083449). The signature was checked; no one was assigned to own the check.
The failure was never cryptographic, it was organizational, and it was invisible to every
tool the operator had.

Agent systems reproduce that failure at machine speed. An agent calls a tool, writes a
file, spends a token budget, sends a message. The runtime logs it — into a log the runtime
itself can rewrite, readable only by someone who trusts the runtime. When a customer, an
insurer or a regulator asks "what did the agent actually do, and who approved it", the
answer is a vendor screenshot.

## Who the user is

Two concrete users:

1. **The operator of an agent fleet** (one to dozens of agents on their own hardware) who
   has to answer for the fleet's actions to a third party — a client, an auditor, an
   insurer — and currently has no artifact to hand over that does not require trusting the
   machine that produced it.
2. **The compliance/risk engineer** at a vendor whose contracts now shift liability onto
   the customer (Meta's commercial terms from 2026-10-30 make the customer assume "any and
   all risks" for model errors; EU Digital Omnibus Art. 88bis widens training-data use).
   They need per-action evidence with a named responsible party, because "the model did it"
   is not a defence.

## Why existing solutions are inadequate

- **Runtime logs** (the agent framework's own `usage_audit.jsonl`, request logs) are
  mutable, host-local, schema-drifting and trust the logging process. A log is a
  convenience; it is not evidence.
- **`pubgate` (this repo, 2026-10-23)** proves *what was published* matches what was built.
  It has no concept of a runtime action.
- **`plugattest` (this repo, 2026-10-24)** proves *what a plugin claims* matches what its
  code does, before install. It cannot speak about a single action taken after install.
- **LLM "audit" skills** — `cloudflare/security-audit-skill` is #1 on GitHub trending at
  45k stars and has not been pushed since 2026-09-14: non-deterministic narration, no
  verifiable artifact, no exit code an auditor can re-run.
- **Package/model signing** proves *who published* an artifact, not *what an agent did*
  with it, and never records that a human owned the outcome.
- **SIEM/log shipping** centralizes logs but still requires trusting the collector and
  proves nothing about tampering with a specific record.

The gap is a portable, self-verifying, append-only record of agent actions in which every
record names the party responsible for verifying it — so an audit reports "N actions with
no named verifier" instead of a green tick.

## What this tool is

A zero-dependency (stdlib only) CLI that:

- **records** one agent action per line into a hash-chained append-only ledger, binding
  agent id, model id + weights digest, policy version, tool, an args hash, the data
  touched, the assigned verifier, human approval (who/when), and outcome;
- **verifies** the chain on a host that does not trust the logging machine — detecting
  edited records, reordering, deleted middle records and truncation (vs. a committed head);
- **exports** a self-contained bundle an auditor can check with no access to the runtime;
- **audits responsibility** — the differentiator that answers eMudhra directly: counts
  actions with no named verifier, self-verified actions, and consequential actions with no
  recorded approval, with a fail-closed exit code for CI.

---

# 2026-11-05 — second justification: the weights-digest field was unfalsifiable

## The problem

`ActionRecord.model_digest` was a string the caller typed, and `audit` could only ask
whether it was non-empty. Measured in the code, not asserted: `cli.py` took
`--model-digest` as free-form input, `audit.py` tested `record.model_digest.strip()`, and
the batch adapter in `sources.py` wrote `""`. So `abcdef` produced the same audit verdict
as a real digest of the wrong model. The ledger's entire model-identity axis — the field a
compliance reviewer reaches for first — was a transcription with no way to be wrong.

The measurement half now exists: `wsaudit` (this repo, 2026-11-04) hashes weights per
tensor and emits a canonical model digest, and `grep -rl wsaudit` across the repo returned
exactly one hit — `INDEX.md`. The instrument and the record were not wired together, which
is exactly the class of gap this ledger exists to expose, sitting inside the ledger.

## Who the user is

The same two people as above, at the moment they are handed a ledger row and asked "was
this the model you think it was?". Today the honest answer is "the row says so". After this
change the answer is one of: a digest recomputed from a manifest of N named tensors, or an
explicit `AAL-007` saying nobody measured it.

## Why existing solutions are inadequate

- **A digest column in a log** is what this replaces: it records what someone typed.
- **`wsaudit` alone** proves the bytes on disk match a manifest. It cannot say which
  actions ran on those weights.
- **Model signing** (`model-signing`, sigstore-style) proves a publisher signed an
  artifact; it needs a vendor key and a network, and it says nothing about a runtime row.
- **Anthropic's provable-inference work and `anthropics/FlashProve`** (845 stars,
  "Not maintained") prove properties of the *computation*. A digest proves *which bytes
  ran*. Neither substitutes for the other, and a research prototype is not a dependency.

## What this change is

`record --model-manifest` recomputes the canonical digest from the manifest's own tensor
list (the value is derived in-process, never copied), refuses a manifest that is
header-only, self-inconsistent or empty, and refuses to record at all when a supplied
`--model-digest` disagrees — exit 2, nothing written. One binding line per bound record is
appended beside the ledger (`<ledger>.manifests.jsonl`), and `audit` treats a digest as
measured only when that line names the same value — the `ws1:` tag alone is not evidence,
because anyone can type it. `verify-binding` answers the auditor's reverse question: which
actions in this ledger ran on these exact weights.

---

# 2026-11-06 — the binding's own provenance was written and never checked

## The problem

Yesterday's change made a digest *measured*: `record --model-manifest` derives it from a
wsaudit manifest and writes a binding line beside the ledger. That line records seven
fields, and four of them — `format`, `tensor_count`, `manifest_sha256`, `manifest` —
were read back by nothing.

```
append_binding   writes: seq, model_digest, format, tensor_count,
                          manifest_sha256, manifest (abspath), recorded_at
load_bindings    returns: Dict[int, str]        # seq -> model_digest ONLY
audit             uses:   bindings.get(seq) == record.model_digest
```

So a MEASURED row asserted "these are the bytes that produced this digest" and no code
path recomputed it. `manifest_sha256` was a claim in a file whose provenance is exactly
what the ledger could not falsify. Concretely: edit the manifest after binding, and the
row still reads MEASURED — the digest in the record is unchanged, the binding still names
it, and the file it came from is never looked at again. Substitution of the *manifest* is
cheap and silent, even though substitution of the *weights* is caught.

The second half is portability. `manifest` is an absolute path, so a ledger handed to
another machine records a location that means nothing there. The artifact stops being
self-describing the moment it leaves the box it was written on — which is the one thing an
evidence ledger cannot afford.

## Who the user is

The same two users as the project's first justification, one step further along. The
operator who exports a ledger is now handing over something that says "measured against
manifest sha256:fb09bc1f…" — and until today, the recipient could only take that on trust.
The auditor on the other machine is the one who needs to re-measure it, and had neither
the fingerprint to compare against nor a path that resolved.

## Why existing solutions are inadequate

- **`wsaudit hash <file> --manifest <M>`** proves the weights still match the manifest. It
  takes both from the command line — a verifier handed only a ledger cannot know which
  manifest to pass it, or that the file at that path is the one originally measured.
- **The digest comparison in `audit`** proves a binding names the same digest. It says
  nothing about the file the digest was derived from.
- **Signing the manifest** (sigstore-style) proves a publisher signed it; it needs a key
  and a network, and it does not help when the question is "is this the file *I* measured
  an hour ago on this box".
- **A bare abspath** is what the sidecar recorded until today: correct on one machine,
  meaningless on every other.

## What this change is

`audit --verify-manifest` re-measures every MEASURED row: it re-opens the recorded
manifest, recomputes its canonical sha256, and compares it with the fingerprint written at
binding time. Three states, never two — `PASS`, `MANIFEST-SHA-MISMATCH` (FLAG, the file
changed after it was measured), and `MANIFEST-UNMEASURABLE` (WARN: gone, unreadable, or a
binding written before fingerprints were taken). "Could not check" is never reported as
"checked and fine". The binding also records `manifest_basename`, so a ledger that moves
with its manifest still verifies by name, and resolution never searches beyond the ledger's
own directory — a same-named file elsewhere is not the same measurement.

---

# 2026-11-07 — the bundle cannot check the two claims the project exists to make

## The problem

`export.py` says what a bundle is, in its own words: "A bundle is the artifact you hand to
someone outside the machine… Verification needs this tool's stdlib code and the bundle.
That is the whole trust base." For immutability that is true: `verify_bundle` re-walks the
chain and a dropped or edited record breaks it.

For the other two legs it is not true, and the file says so by omission. `build_bundle`
emits exactly five keys — `format`, `generated_at`, `count`, `head_hash`, `entries`.
`grep -n "audit\|binding\|manifest\|provenance" src/actledger/export.py` returns one hit,
and it is the docstring. So:

* **Responsibility** (AAL-001/002/003) cannot be judged off-machine, because the findings
  that judge `verifier` / `approved_by` / `approved_at` are computed by `audit`, which
  nothing in the export path calls. The receiver holds the fields and no verdict.
* **Provenance** (AAL-007) cannot be judged either, because `record.to_dict()` emits
  `model_digest`, `models.py` records a `ws1:…` string, and no binding travels with it.
  Every `ws1:` digest in a bundle is therefore a transcription that looks exactly like
  evidence — which is the failure AAL-007's own detail string names ("a typed digest is a
  transcription, not evidence"). The claim is in the artifact; the proof is on the machine
  the artifact left.

`cli.py:225` makes it concrete: `build_bundle(Ledger(args.ledger).entries())` — the
bindings are not even loaded, so the exporter could not carry them if it wanted to.

## Who the user is

The same auditor as before, one step further out. They are handed a `.bundle.json` and
nothing else: no ledger, no sidecar, no manifest directory, no shell on the exporting
machine. Today they can prove the records were not altered. They cannot prove the bundle's
declared posture is the posture the records actually earn, and they cannot tell a digest
that a tool derived from a digest someone typed. A verifier who trusts the artifact
currently asserts more than they can support — the precise failure this tool exists to
prevent, reproduced in its own exit door.

## Why existing solutions are inadequate

* **"Just ship the ledger and sidecar"** is what `export` was supposed to replace: the
  sidecar sits beside the ledger as a file path, and the whole point of a bundle is that
  the artifact is one file and the trust base is stdlib code.
* **"Put the manifest in the bundle"** does not scale and does not answer the question —
  a 45 KB manifest per row bloats the artifact, and the manifest is still a transcription
  unless its fingerprint is checked.
* **"Trust the declared verdict"** is backwards. A declared verdict that the artifact
  cannot recompute is a claim, not a finding.
* **Re-measuring the manifest off-machine is impossible by construction** — the file is
  not in the bundle. The honest answer is a third state, not a pass.

## What this change is

Bundle format `actledger-bundle/2`. The bundle now carries `bindings` (each row's full
derivation: digest, tensor count, format, manifest basename and fingerprint — never the
abspath, which means nothing on the receiving machine) and `audit` (the posture computed
at export time by the same `audit` code). `verify-bundle` recomputes both from the
artifact's own records and bindings:

* every `ws1:` digest must be corroborated by a binding that names the identical digest —
  `BINDING-MISMATCH` (FLAG) when one names a different digest, which is the forgery case,
  because bindings live outside the hash chain and the bundle is attacker-reachable;
* the declared posture must equal the recomputed one — `AUDIT-DIVERGES` (FLAG) otherwise,
  so "declared PASS" cannot travel with records that do not earn it;
* `BINDINGS-ABSENT` (exit 2, not pass) when a v1 bundle or a `--no-provenance` export
  carries no bindings at all. An old bundle must read as *not checkable*, never as clean.

The manifest fingerprint leg stays explicitly unproven off-machine and is named as such
(`MANIFEST-NOT-BUNDLED`, INFO): the bundle says what it cannot prove rather than implying
it did. A receiver who is also handed the manifest still re-measures it with
`audit --verify-manifest` — unchanged from 2026-11-06.
