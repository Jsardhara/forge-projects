# skillbom

**A capability bill of materials for the skills installed on a Hermes host.**

A skill is loaded with the full authority of the profile that loads it: shell, network,
home directory, environment. `skillbom` walks the live skill directories and emits one
ledger record per installed skill - what it declares, which scripts it ships, what those
scripts are *statically* capable of - then rolls the fleet up so duplication and drifted
copies are a measurement instead of a rumour.

It is deliberately **not** a verdict. `plugattest` already answers "does this package's
manifest match its code"; `secretsurface` answers "where does key material live".
`skillbom` answers "what authority is installed here, and did it change since last run".

Read-only. Offline. Never executes a skill script. Never prints a credential value.

## Install

Zero dependencies, standard library only. Nothing to install:

```sh
cd 2026-11-01-skillbom
PYTHONPATH=src python3 -m skillbom --help
```

## Usage

```sh
# every profile's skills dir on this host, human-readable
PYTHONPATH=src python3 -m skillbom

# machine-readable, and keep the ledger so tomorrow can diff against it
PYTHONPATH=src python3 -m skillbom --json --ledger-out ledger/2026-11-01.json

# what changed since the last ledger
PYTHONPATH=src python3 -m skillbom --diff ledger/2026-11-01.json

# one profile only, plus the shared store
PYTHONPATH=src python3 -m skillbom --root ~/.hermes/profiles/forge/skills --include-global

# the authority shortlist: skills holding the most capabilities
PYTHONPATH=src python3 -m skillbom --top 15
```

### Options

| Flag | Meaning |
|---|---|
| `--root PATH` | Audited skill directory (repeatable). Without it: `~/.hermes/profiles/*/skills`. |
| `--include-global` | Also audit `~/.hermes/skills` (the shared/default store). |
| `--json` | Emit the ledger as JSON on stdout instead of the text report. |
| `--ledger-out PATH` | Write the JSON ledger to `PATH` (for a later `--diff`). |
| `--diff PATH` | Diff the current scan against a previous ledger file. |
| `--top N` | Show the `N` highest-authority skills (default 10, `0` disables). |
| `--quiet` | Suppress the text report; exit code only. |

## What it measures

Per skill: `profile`, `name`, `path`, `SKILL.md` sha256, `mtime`, declared tools
(`tools:` / `allowed-tools:`), frontmatter validity, and one entry per script file with its
own sha256, size, and static capability signals.

Capabilities are read from the script bodies, never from what the skill claims:

| Capability | Matched on (examples) |
|---|---|
| `network` | `curl`, `wget`, `urllib.request`, `requests.`, `httpx.`, `fetch(`, `socket.` |
| `exec` | `subprocess`, `os.system`, `os.popen`, `sh -c`, `spawnSync`, `execSync` |
| `code_eval` | `eval(`, `exec(`, `new Function`, `pickle.loads`, `yaml.load(` |
| `fs_write` | `write_text`, `write_bytes`, `writeFile`, `open(...,"w")`, `shutil.rmtree`, `unlink(` |
| `credentials` | `os.environ`, `os.getenv(`, `.env`, `*_API_KEY`, `Authorization:`, `keyring` |
| `hermes_surface` | `.hermes`, `state.db`, `.hermes/vault`, `profiles/`, `memory/` |

## Exit codes

Fail-closed, same contract as the rest of this repo's attestation tools:

| Code | Meaning |
|---|---|
| `0` | Ledger built; no divergent copies, no drift against `--diff`. |
| `1` | A finding: copies of one skill disagree, or the ledger drifted. |
| `2` | Something could not be measured (missing root, unreadable file). Never read as clean. |

## Fleet rollup

- **Distinct skills vs copies.** The same skill installed in nine profiles is one skill and
  nine copies. The report counts both; only the copy count is the attack surface.
- **Divergence.** Skill name -> distinct `SKILL.md` hashes across copies. More than one hash
  means nine profiles are running different instructions under one name, with no version
  signal anywhere on the host.
- **Drift.** `--diff` reports added / removed / changed skills and changed scripts by
  content hash, so "a skill quietly changed" becomes a line in a report.

## Limits (stated, not hidden)

- Signals are regex over text. A capability reached through a helper the skill does not
  ship, an obfuscated payload, or a base64 blob is not visible here.
- A script larger than 512 KiB is hashed but only its first 512 KiB is classified, and the
  record says `truncated: true`.
- Directory names starting with `_` or `.` (e.g. `_trash`, `.archive`) are skipped and
  counted, not silently dropped.
- This measures *installed text*, not *runtime behaviour*. A skill that talks its way into
  a shell without a single `subprocess` call is invisible to a static scan; that gap is
  why `plugattest` and this tool are complements, not substitutes.

## Tests

```sh
cd 2026-11-01-skillbom
PYTHONPATH=src python3 -m unittest discover -s tests
```
