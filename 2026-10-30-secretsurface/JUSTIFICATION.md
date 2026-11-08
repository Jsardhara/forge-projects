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

---

## 2026-11-08 — the scanner could not tell a published secret from an ignored one

**Source:** Lens daily intel 2026-11-08, top build call, score 6.5
(`0.5·urgency(5) + 0.25·market(7) + 0.25·feasibility(9)`).

This is not a new project. It is a defect in the one shipped nine days ago, in the signal
that decides how a finding is ranked.

### The defect, measured

Apiiro traced 2,539 real secrets in 1,994 public repositories to a single artefact class:
`.claude/settings.local.json` — a file an agent tool writes into the project folder,
containing whatever command the user approved with "don't ask again", secret included.
**1,122 of 104,185 public copies hold a real secret**, across 63 organisations.
Nothing about that path says "private", so it is committed with the code.

`secretsurface` could not express that. Two measured facts, both reproduced before any
code changed:

1. `blast.py:_in_git_worktree` walked up looking for a `.git` and returned
   `in-git-worktree`. That is true for **every** file in a repository — committed, about
   to be committed, or excluded — so it was a constant, and a constant carries no
   information. Worse, it was *almost* a tautology inside the shipped scan: the walker
   already drops gitignored files, so every finding the tool could emit came from a file
   that `git add .` would publish, and a signal that is true for everything it can see
   tells the reader nothing.
2. `classify.py:CLASSES` had no member for a committed agent config, so
   `.claude/settings.local.json` fell to `unknown` — the same bucket as a plain file in a
   directory that is not a repository at all. A published key and a local-only key were
   indistinguishable in the output.

### Where Lens was wrong, and why it matters

The proposal said the tool "overstates risk on every properly-ignored file". Measured:
it cannot. `walk.py:131` skips a `.gitignore`d file before it is ever read, so no finding
is emitted for one. The overstatement is real but reachable by a **different** route the
note did not name: the walker implements only `.gitignore`, not `$GIT_DIR/info/exclude`
or `core.excludesFile`, so a file excluded by those **is** scanned and was reported as
`in-git-worktree`. That is the case the new tests pin, because it is the case that
actually happens.

Taking the note at face value would have produced a fix that guards against a state the
code cannot reach while leaving the reachable one alone.

### What changed

| piece | job |
|---|---|
| `blast.publication_state` | five states from git itself — `git-tracked`, `git-untracked-unignored`, `git-ignored`, `no-git-worktree`, `git-unknown` — via `ls-files --error-unmatch` and `check-ignore -q` |
| `blast.publication_rank` | ordering key; `git-unknown` ranks **above** `git-ignored` so a git failure never reads as safety |
| `classify` | `committed-config` class for `.claude/settings*.json`, `.mcp.json`, `.cursor/`, `.continue/`, `AGENTS.md`, `.aider*` |
| `scan._exposure_key` | published-ness first, class second, then path/line |
| `report.CLASS_ORDER` | now imports `classify.CLASSES` — renderer cannot disagree with classifier |

Two deliberate deviations from the proposal:

- **A definitive "not a repository" is `no-git-worktree`, not `git-unknown`.** The note
  asked for `unknown` when there is no `.git`; but git ran, answered, and its answer is
  *this file cannot be committed from here*. Collapsing that into `unknown` would make
  every non-repo path rank as unknown and erase a fact the operator can use. `unknown` is
  reserved for git failing to answer (absent binary, timeout, corrupt index).
- **`git-tracked` is still tracked when an ignore pattern also matches it.** Real git
  keeps tracking a file added to `.gitignore` after the fact; asking `check-ignore` first
  would have called a published file ignored. Order is `ls-files`, then `check-ignore`.

### Proof

- 136 tests (was 105), 31 new. RED was watched: 30 new tests, 8 failing on classify and
  ordering before the implementation, and the pre-existing
  `test_file_inside_git_worktree_is_flagged` failed exactly where it asserted the retired
  signal — rewritten to assert `git-unknown`, not deleted.
- Every publication test builds a real git repository in `tmp_path` and lets git decide;
  none stub the answer.
- Failure modes pinned: missing git binary → `git-unknown`; git exiting 128 →
  `git-unknown`; a bare `.git` directory with no repository → `git-unknown`; none of
  these may return `git-ignored`.
- Real host, 2026-11-08: 10,503 files scanned, 50,752 skipped and reported, 264 findings
  in 17.2 s. All 264 are `no-git-worktree` — this host's profile tree is not a
  repository — so this change moves **no finding** here. That is reported as it is: the
  value is in repository scans, where published-ness decides the order, and it is
  demonstrated in the scratch repos above, not claimed from the host.
- Fixture discipline, learned the hard way on 2026-10-30: the first probe used
  `AKIAIOSFODNN7EXAMPLE` and returned zero findings because the tool's own placeholder
  filter dropped it — a green probe measuring nothing. The shipped fixtures use a
  non-placeholder value.
