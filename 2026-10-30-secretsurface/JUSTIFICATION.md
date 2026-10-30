# Project Justification — secretsurface

**Built:** 2026-10-30 · **Source:** Lens daily intel 2026-10-30 (top build call, score 7.3)

## The real problem

Every answer to "where are our secrets?" starts and ends with `.env`. That answers a
different question than the one being asked. `grep .env` tells you whether a value is in
a specific file; it does not tell you **where key material actually lives** on the host,
and it is structurally incapable of telling you when the answer is somewhere you never
modelled as a secret store.

On a multi-agent host this gap is not theoretical. A measured read of `~/.hermes/profiles`
on this machine (`jarmes`, 2026-10-30) finds key-shaped material in **8 files outside
`.env` in the `forge` profile alone**, and they are the wrong *kind* of file:

- an append-only **activity log** (`foreman_activity.jsonl`) — logs get tailed, copied,
  shipped and pasted into issues; nobody treats a log as a credential store;
- **five curator backup blobs** under `.curator_backups/blobs/` — snapshots of skill
  directories. Nobody models backups as a secret store, so nobody rotates them, and a
  backup outlives the rotation that was supposed to retire the key;
- **`.env.bak.si09-*` env backups** — superseded keys that were never revoked. The whole
  point of the SI-09 rotation was to kill those keys; a `.bak` makes the rotation partial
  while looking complete;
- **doc fixtures** in skill documentation and `${...}` templates — probably examples, but
  "probably" is the operative word, and an unclassified hit is indistinguishable from a
  real one until someone reads it.

The failure is silent in the unsafe direction: the cheap check reports "clean" because the
secrets are not where the check looks.

## Who the user is

The operator of a small fleet of autonomous agent profiles on one Linux box — someone who
rotated a credential once, believes it is dead, and has no way to prove the old value is
not still sitting in a backup blob and an activity log. Secondary user: any agent or
automation that has to hand a **revocation path list** to a human without ever handling
the secret itself.

## Why existing solutions are inadequate

- **gitleaks / trufflehog** answer "find secrets", and they answer it well. They are
  built for *repositories and commit history*, and they report a location — they do not
  classify *what kind of store* the hit lives in, which is the entire question here
  ("is this a live `.env`, a superseded backup, an append-only log, or a doc example?").
  They also default to printing/annotating matched values, which creates a second leak in
  the terminal scrollback of an automated job.
- **AgentVault (2026-07-10)** governs *runtime* secret scoping for agents. **apk-signal
  (2026-07-08)** finds hardcoded secrets inside APK binaries. **mcpshield (2026-07-19)** checks
  secret *scoping declarations* in an MCP manifest. **plugattest (2026-10-24)** compares
  declared capabilities against capabilities the code uses. All four sit on other layers;
  none walks a live multi-profile host and returns "here is every non-`.env` place key
  material survives, by class, with a blast-radius and a revoke list".
- **A secret rotator** would be the wrong tool to build: rotation is operator-only (T4),
  and automating deletion of another profile's credentials is how you take down a fleet.

So the uncovered slice is exactly: **classification + blast radius, read-only, offline,
never echoing the value.** `secretsurface` is that slice, and nothing else.

## What it deliberately is not

Not a gitleaks clone (occupied, mature, better funded than three hours of mine) · not a
rotator (T4) · not a pre-commit hook (different machine, hooks get bypassed) · not a tool
that writes key material to disk or stdout. It emits paths, line numbers, pattern ids and
a 4-character sha256 fingerprint — enough to prove two sightings are the same value,
useless to anyone who intercepts the report.
