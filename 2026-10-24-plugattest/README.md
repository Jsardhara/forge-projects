# plugattest

**Does this plugin only do what its manifest says it does?**

A plugin or skill is not a passive file. It ships instructions an agent obeys and, often,
scripts that run with the agent's own privileges: its API keys, its filesystem, its
network, its shell. The install decision today is made entirely from a manifest the
publisher wrote. Nothing compares that claim to the code.

`plugattest` does that one comparison — **declared capabilities vs detected
capabilities** — deterministically, offline, with zero external dependencies.

```
$ plugattest ./some-plugin
plugattest: some-plugin
  declared: network
  detected: code_eval, credentials, fs_write, network, shell
  verdict:  FLAG (score 100/100)
  PA-001 FLAG  install.js:12 -- capability used but never declared (signal: node-write) [fs_write]
  PA-004 FLAG  package.json -- auto-execution hook 'postinstall' runs on install but auto_hook is not declared [auto_hook]
  PA-002 INFO  package.json -- capability declared but no use detected in the package source [network]
```

## Why not an existing tool

| Existing approach | What it answers | What it misses |
|---|---|---|
| Runtime sandbox (e.g. NVIDIA OpenShell) | what a process may do while running | what the package *intended*; cannot fail an install before execution |
| LLM "security audit" skills | a general code review | non-deterministic, no manifest baseline, no CI exit code |
| Package signing / attestations | *who* published the artifact | *what capabilities* it uses — a signed package can still read `~/.ssh/id_rsa` |
| [`pubgate`](../2026-10-23-pubgate) | is the wheel byte-identical to upstream source | capability semantics; no notion of plugin manifests or skill frontmatter |

Signing proves the seller. `plugattest` checks the seller's claim against the code.

## Install

Standard library only. Nothing to install:

```sh
PYTHONPATH=src python3 -m plugattest <package-dir>
```

or install the console script:

```sh
pip install .
plugattest <package-dir>
```

## Manifest forms understood

| File | Used for |
|---|---|
| `package.json` | npm-shaped plugins (`capabilities`, `permissions`, `requires_capabilities`, plus `preinstall`/`install`/`postinstall` hooks) |
| `plugin.json`, `.claude-plugin/plugin.json` | plugin manifests |
| `SKILL.md` frontmatter | agent-skill packages (first frontmatter block only; capability keys in the body are prose, not a claim) |

Only the package's **own** code is scanned. `node_modules`, `vendor`, `site-packages`,
`.git`, caches and build output are skipped: a dependency's capabilities are the
dependency's to declare. Documentation is skipped — prose mentioning `subprocess.run` is
not a call.

## Capabilities

`network` · `shell` · `fs_write` · `credentials` · `code_eval` · `auto_hook`

Each manifest token is normalized through an alias table (`fs:write`, `filesystem`, `fs`
→ `fs_write`; `net.egress` → `network`; …), so a package declaring `fs:write` is not
flagged for using the filesystem.

## Findings

| Code | Severity | Meaning |
|---|---|---|
| `PA-001` | FLAG | capability used in code but absent from the declaration |
| `PA-002` | INFO | capability declared but no use detected (over-declaration) |
| `PA-003` | WARN | manifest exists but makes no capability claim at all, while code uses capabilities |
| `PA-004` | FLAG | auto-execution hook (`postinstall`/`install`/`preinstall`) without a declared `auto_hook` |
| `PA-005` | FLAG | no manifest at all, yet capabilities are used — fail closed |
| `PA-006` | WARN | declared capability token is not a known capability and cannot be attested |
| `PA-007` | WARN | manifest exists but could not be parsed |

**Verdict is severity-dominant**: the worst single finding decides (PASS → INFO → WARN →
FLAG). The 0-100 score is a magnitude display for gates, never a band-crossing
mechanism — stacked warnings cannot promote themselves to a FLAG.

## Exit codes

| Code | Meaning |
|---|---|
| `0` | clean at or below the `--fail-on` threshold |
| `1` | findings at or above the threshold |
| `2` | usage error, or the path is not a directory |

`--fail-on {none,info,warn,flag}` defaults to `warn`, so an installation gate fails on an
undeclared capability namespace rather than on informational notes.

## CI

```yaml
- run: PYTHONPATH=src python3 -m plugattest ./my-plugin --fail-on flag
```

```sh
# pre-commit
plugattest . --fail-on warn
```

## JSON

```sh
plugattest ./my-plugin --json
```

```json
{
  "package": "my-plugin",
  "verdict": "FLAG",
  "score": 100,
  "declared": ["network"],
  "detected": ["fs_write", "network"],
  "findings": [
    {"code": "PA-001", "severity": "FLAG", "location": "install.js:12",
     "message": "capability used but never declared (signal: node-write)",
     "capability": "fs_write"}
  ]
}
```

## Tree mode

```sh
PYTHONPATH=src python3 scripts/attest_tree.py <marketplace-root>
```

Attests every directory containing a `SKILL.md`, `package.json` or `plugin.json` and
prints a verdict table. Use it to size a marketplace's disclosure gap in one shot.

## What it is not

- **Not a sandbox and not a malware scanner.** It reports capability-vs-claim mismatch,
  not intent. A package that declares `shell` and uses `shell` is clean here, and that
  says nothing about whether the shell command is hostile.
- **Not a vulnerability scanner.** Point it at capability scope, not CVEs.
- **Not exhaustive.** Detection is a signal table; a capability exercised in a way the
  table does not model will not be seen. Treat `PASS` as "no mismatch found by this
  table", not as proof of innocence.

## Tests

```sh
cd 2026-10-24-plugattest && PYTHONPATH=src python3 -m unittest discover -s tests
```
