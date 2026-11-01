# kcheck

**Is THIS host's kernel in a known kernel CVE's affected range — and is it on the
demonstrated attack path?**

Read-only, offline, keyless, stdlib only. No root, no network, no package manager, no
service restarts. One binary, one checked-in dated table, two separate answers.

The question it exists to answer is the one a CVE feed cannot: NVD says *CVSS 9.8,
remote, unauthenticated*. It does not say whether **your** kernel is below the fix, or
whether the feature the exploit needs is even switched on here. `kcheck` measures both
on the box it runs on.

## Why this exists

On 2026-11-01 the daily pipeline flagged **CVE-2026-98432** (Linux IPv4 TCP use-after-free
on the MPTCP path, CVSS 9.8, remote + unauthenticated) with the version range
*unverified*, so the build slot correctly went to something else. The range was verified
55 minutes later — and this host turned out to be in it. A verified, deadline-sensitive
fact had missed its slot by one tick. `kcheck` is that fact, made re-runnable.

## What it measures

| Signal | Probe | Failure mode |
|---|---|---|
| running kernel | `uname -r` | unreadable → exit 2 |
| installed kernel packages | `dpkg-query -W -f='${Package} ${Version}\n' 'linux-image-*'` | unreadable → uname fallback, flagged |
| distro + release | `/etc/os-release` | unknown distro → **exit 2** |
| MPTCP switch | `sysctl net.mptcp.enabled` | unreadable → `None`, never `0` |
| MPTCP listeners | `ss -Mln` | unreadable → `None`, never "zero listeners" |

No `sudo`, no `apt`, no `dnf`, no `nft`, no `iptables`, no sysctl write, no socket opened
outward. The tool reads four things and prints a verdict.

## Install

None. Python 3.8+ standard library.

```bash
cd 2026-11-01-kcheck
./kcheck                  # human report
./kcheck --json           # machine rollup
./kcheck --cve CVE-2026-98432
PYTHONPATH=src python3 -m kcheck          # equivalent module form
PYTHONPATH=src python3 -m kcheck --table data/fixed_versions.json
```

## Exit contract (CI-friendly)

| code | meaning |
|---|---|
| `0` | clean — the installed kernel is not in range of any checked CVE |
| `1` | findings — the installed kernel is in range (including `fix_pending`) |
| `2` | unmeasurable — no verified fix row for this distro, or a probe could not be read |

`2` is the important one. **Exit 2 is mandatory whenever the fixed version for the
running distro is unknown.** A tool that answers "not vulnerable" when it has no data is
worse than no tool: it converts an unmeasured host into a green dashboard tile.

`fix_pending` — the vendor confirms the range and has *not released* a fix — is **not**
exit 2. It is a confirmed finding: exit 1. Modelled as a distinct state because
"vulnerable but unpatchable" is neither "vulnerable, patch available" nor "fixed".

## Example (live, this host, 2026-11-01T06:39Z)

```
kcheck -- is THIS host's kernel in a known CVE's range?  (2026-11-01T06:39:53Z)

HOST (measured, not inferred)
  running kernel    7.0.0-38-generic
  installed image   linux-image-7.0.0-38-generic 7.0.0-38.38
  distro            ubuntu 26.04 (resolute)
  mptcp             net.mptcp.enabled = 1 (enabled)
  mptcp listeners   5 listener(s)
  exposure          tailnet, localhost (100.64.0.0/10, 127.0.0.0/8, fd7a:115c:a1e0::/48)

CVE-2026-98432  VULNERABLE  fix_pending  CVSS 9.8
  Linux IPv4 TCP use-after-free on the MPTCP path (remote, unauthenticated)
  running           7.0.0-38-generic (package 7.0.0-38.38)
  fixed target      7.0.0-43.43 -- NOT RELEASED (vendor: fix in progress)
  gap               5 ABI levels behind (38 -> 43)
  attack path       ON PATH -- MPTCP listener reachable from a remote peer (probe:
                    ss -Mln + sysctl net.mptcp.enabled); 5 listener(s)
  exposure          tailnet, localhost
  tracker           https://ubuntu.com/security/CVE-2026-98432 (retrieved 2026-11-01T06:26:00Z)
  provenance        0 days old

exit: 1 -- findings -- the installed kernel is in range, or the attack path is reachable
```

### The exposure reading, stated plainly

All five MPTCP listeners on this host bind **`127.0.0.1`** or **`100.64.0.0/10`
(Tailscale)** — three on the tailnet address `100.107.170.75` / its IPv6 equivalent and
one on loopback. **Nothing is bound to the LAN interface `192.168.0.41` and nothing is
internet-facing.** The demonstrated path is **tailnet-reachable, not
internet-reachable**.

That is a real reduction in exposure and it is not a clean bill of health: every tailnet
peer is a trust boundary this host does not fully control, and the listeners are owned by
a Go program (Tailscale itself) whose memory the kernel is faulting inside. The tool
prints the scopes and the prefixes it matched so that sentence can be checked, rather
than asserting "internal only" and expecting trust.

## The two axes are separate booleans, on purpose

`in_range` and `on_demonstrated_path` are reported independently and never collapsed:

- **in range + no listener is still in range.** A host one `systemctl start` away from
  the path is not safe, and a merged verdict would report it as safe.
- **not in range + listener is still exposure.** The listener set is a fact about the
  host that outlives this CVE.

Only `in_range` pins the exit code. A **patched host that is still listening is exit 0
with the listener printed**, not exit 1 forever — a gate that is permanently red is a
gate that gets switched off, which is how a security check becomes decoration. This is a
deliberate, documented deviation from the strictest reading of "1 = in range *or* on
path"; the path axis is always visible in both outputs, so nothing is hidden, and
`--json` carries `on_demonstrated_path` for a consumer that wants to gate on it.

## Version comparison is the whole tool

`7.0.0-38` vs `7.0.0-43.43` compares as strings as **greater** — a five-patch-levels-short
kernel reported as patched. `7.0.0-9` vs `7.0.0-10` is the same trap: string compare says
9 > 10. `src/kcheck/dpkgver.py` implements dpkg's `verrevcmp`/`order` literally (epoch,
then alternating non-digit/digit walk, `~` before end-of-string, digits numerically,
letters before punctuation). The boundary table in `tests/test_dpkgver.py` pins
`7.0.0-38` → vulnerable, `7.0.0-43.42` → vulnerable, `7.0.0-43.43` → fixed,
`7.0.0-44` → fixed.

The installed version comes from the **package DB** (`7.0.0-38.38`), not from `uname -r`,
because the ABI suffix is what makes the comparison exact. `uname -r` is used only to
identify *which* package is running, and stripped of its flavour suffix as a fallback
when the package is absent.

## The table is data, and it dates itself

`data/fixed_versions.json` — one row per CVE, one row per distro inside it:

```json
"ubuntu-26.04": {
  "fix_state": "pending",
  "fixed_version": "7.0.0-43.43",
  "status_text": "26.04 LTS resolute | Vulnerable | work in progress in 7.0.0-43.43",
  "source_url": "https://ubuntu.com/security/CVE-2026-98432",
  "retrieved_at": "2026-11-01T06:26:00Z"
}
```

- Validated **at load**: a missing `source_url`, a missing `retrieved_at`, an
  unrecognised `fix_state` or an unparseable `fixed_version` fail loudly with the file
  named. A dead path is discovered at 06:15 in v1; here it is discovered on startup.
- Every row carries its own provenance, and a row older than `stale_after_days` (7) is
  printed as **STALE, re-verify against the tracker** and flagged in `--json`
  (`provenance_age_days`, `provenance_stale`). Staleness is loud but not fatal: making it
  fatal would pin the exit code at 2 forever and the gate would be ignored.
- Only verified rows exist. There is no Ubuntu 24.04 row, no RHEL row, no Arch row — a
  distro with no row is **exit 2**, which is the honest answer and the whole point.

Updating the table is a deliberate, dated act. There is no network client in this tool.

## Mitigation: a pointer, never an action

The advisory's mitigations are an nftables `u32` rule (custom TCP-option matching) and
`net.mptcp.enabled = 0`, both of which are host-firewall/kernel changes and both of which
can break networking. **`kcheck` prints the pointer and never runs them.** It does not
shell out to `nft`, `iptables`, or `sysctl -w`, and it never writes a config file. The
commands live in
`/home/jyot/.hermes/profiles/lens/outputs/lens-daily-intel.md` under *AMENDMENT —
06:26Z*; applying them is a T3/T4 operator decision. The real fix is the vendor kernel.

## Limits (stated, not implied)

- The answer is only as good as the table's `retrieved_at`. A stale row is flagged, not
  corrected — this tool does not talk to a CVE feed.
- `100.64.0.0/10` is carrier-grade NAT, not a range Tailscale owns. On this host it is
  the Tailscale interface; the scope is labelled `tailnet` and the matched prefix is
  printed next to it so the label can be argued with.
- `on_demonstrated_path` is a *listener* test for this CVE's MPTCP precondition. It is
  not an exploit attempt: it proves the precondition is reachable on this host, not that
  this host is exploitable. It also cannot see an in-kernel listener path that holds no
  socket at all.
- One host at a time, by design. There is no remote mode, no inventory file, no agent.
- Kernel CVEs whose demonstrated path is not a socket property (e.g. a filesystem bug
  behind a mount option) need a new `attack_path` probe; the framework takes one per
  row, but only `mptcp` exists today.

## Tests

```bash
PYTHONPATH=src python3 -m unittest discover -s tests      # 98 tests
```

Fixture transcripts in `tests/helpers.py` are recorded from this host (`dpkg-query`
output including two half-installed packages that print an *empty* version, real
`ss -Mln` output with bracketed IPv6). The suite covers the version-compare boundary
table, table validation, all four probe parsers, both verdict axes, every exit code, the
`./kcheck` launcher, and one live run that asserts the recorded measurement — skipped
automatically on a host whose kernel is not `7.0.0-38*`.

Exit-path demonstration:

```bash
python3 demo_exit_paths.py     # prints exit 1 / 2 / 0 against fixtures
```

## Scope

Not a scanner (local only, no remote probing), not a package manager (never
`apt`/`dnf`/`sudo`), not a mitigation applier (no `nft`/`iptables`/sysctl writes), not a
CVE feed client (no network; the table is checked in and dated).
