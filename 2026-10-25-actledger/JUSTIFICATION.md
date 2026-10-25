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
