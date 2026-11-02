# cvewatch

**When does this host leave a known CVE's affected range?**

Read-only, keyless, stdlib only. One anonymous GET to one allowlisted host per CVE, a real
dpkg version comparison against the kernels actually installed here, and a diff against the
previous run's saved state — so the only thing that ever alerts is a **transition**.

`kcheck` (built here 2026-11-01) answers *"am I in the range?"*, once, from a checked-in
table. `cvewatch` answers *"when do I get out?"* for as long as the fix is pending, and it
notices when the answer changes. Neither subsumes the other: `kcheck` works offline with no
network and no page parse; `cvewatch` follows the live tracker so a released fix is not
missed by a stale table.

## Why this exists

On 2026-11-02 Ubuntu's tracker for **CVE-2026-98432** (Linux IPv4/TCP use-after-free on the
MPTCP path, CVSS 9.8, remote unauthenticated) listed `7.0.0-43.43` as a *target* version,
"work in progress" — not a released package. This host runs `7.0.0-38.38`. For as long as
that stays true the only question that matters is "when do I get out?", and the only thing
answering it was a person refreshing a web page. A kernel upgrade is operator-only work;
*noticing* that the fix shipped is not. `cvewatch` is that noticing, made re-runnable.

## What it measures

| Signal | Source | Failure mode |
|---|---|---|
| per-release fix status | Ubuntu CVE tracker table | page unreadable → `UNKNOWN`, exit 2 |
| fix target version | "work in progress in X" / "fix released in X" | absent → `VULNERABLE`, no target claimed |
| installed kernels | `dpkg-query -W -f='${Package} ${Version} ${source:Package}'` | failure → reported, exit 2 |
| this host's release | `/etc/os-release` | missing → exit 2 |
| version ordering | local dpkg `verrevcmp` port | unit-tested against real `dpkg --compare-versions` |

No `sudo`, no `apt`, no package install, no service restart, no root. The tool stops at
"the fix is out, here is the version to install"; installing it is the operator's decision.

## Usage

```bash
# one CVE, current host, with a transition report
PYTHONPATH=src python3 -m cvewatch --cve CVE-2026-98432 --state ~/.cache/cvewatch/state.json --diff

# a watch list, machine-readable, for a cron
PYTHONPATH=src python3 -m cvewatch --cve-file cves.txt --json --quiet --state state.json

# offline: replay a saved page
PYTHONPATH=src python3 -m cvewatch --page saved.html --cve CVE-2026-98432 \
    --no-host --release 26.04 --installed linux-image-7.0.0-38-generic=7.0.0-38.38
```

Exit contract: **0** patched / not applicable / ignored, **1** still vulnerable,
**2** could not measure (missing release row, failed fetch, unreadable host). Exit 2 is never
folded into 0 — "could not measure" is not "clean".

## Verdicts

| Verdict | Meaning |
|---|---|
| `VULNERABLE_FIX_AVAILABLE` | the fix is released and this host is below it — act now |
| `VULNERABLE` | tracker says vulnerable, no fix version published |
| `VULNERABLE_PENDING_FIX` | fix not built yet; the target version is reported |
| `UNKNOWN` | could not measure — release row absent, page unreadable, no matching package |
| `PATCHED` | installed version is at or above the fix |
| `IGNORED` | tracker marked the row ignored, reason carried in `detail` |
| `NOT_IN_RELEASE` | this package does not ship for that release |

Ranking is worst-first: `VULNERABLE_FIX_AVAILABLE` > `VULNERABLE` > `VULNERABLE_PENDING_FIX`
> `UNKNOWN` > `PATCHED` / `IGNORED` / `NOT_IN_RELEASE`.

## State and transitions

`--state PATH` (default `cvewatch-state.json`) stores one entry per CVE: verdict, fix target,
release, and the installed binaries with versions. With `--diff`, each run prints only what
changed: `new_cve`, `verdict_changed`, `target_version_changed`, `kernel_changed`. A second
identical run prints nothing — that is the point. Dropping a CVE from the watch list is not
an alert.

The save is atomic (`tmp` + `os.replace`): a half-written state file would look like a kernel
change on the next run.

## Tests

```bash
cd 2026-11-02-cvewatch && PYTHONPATH=src python3 -m unittest discover -s tests
```

92 tests. The parser is exercised against `tests/fixtures/ubuntu_cve_excerpt.html`, a genuine
12-row excerpt trimmed from the page Ubuntu served on 2026-11-02 (rowspan structure intact),
plus inline snippets for status variants that page did not contain. The version comparator is
cross-checked against real `dpkg --compare-versions` when dpkg is present. Network is not
touched by the suite: `test_fetch` runs a real local `http.server`, and the CLI tests read the
fixture file.

## Limits

- HTML parsing, not an API. A tracker redesign breaks the parser; the failure is loud
  (`UNKNOWN`, exit 2), not silent, because an unknown status is kept as `unknown`.
- One CVE page per call unless `--cve-file` is used; each CVE costs one GET. No rate-limit
  handling — a watch list of dozens should be spaced by the cron, not hammered in one burst.
- It reports the kernel *package* version. A custom-built or livepatched kernel with an
  unpatched source tree is invisible here.
- Exposure re-derivation (e.g. MPTCP enabled + listeners for this CVE) is deliberately not
  implemented: `kcheck` already measures the demonstrated attack path, and duplicating that
  here would double the probes for one signal. Compose the two tools.
- No install action, by design. The last line is a version and an operator instruction.
