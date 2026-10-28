# tsattest

**Is this host actually running the Tailscale SSH mitigation, or does only the config
file say so?**

`tsattest` answers three questions about the local Tailscale node, read-only and offline:

1. **Which security bulletins apply to this node?** - not "is it behind latest", but
  per-bulletin applicability against the features actually in use here (SSH on? serve
  configured? unix backend? how many mounts? TLS?).
2. **Is Tailscale SSH on?** - decided from `tailscale debug prefs` -> `RunSSH`, never from
  `tailscale status --json` -> `Self.SSH_HostKeys`.
3. **Is `TS_SSH_DISABLE_FORWARDING` loaded in the *running* process?** - with the three
  answers kept apart: **declared** (in `/etc/default/tailscaled`), **actual** (in
  `/proc/<pid>/environ`), **unmeasurable** (root-only read refused).

## Why the second question exists

On the machine this was written on, in the same minute:

```
$ tailscale status --json | jq .Self.SSH_HostKeys
null            # reads as "Tailscale SSH is off"
$ tailscale debug prefs | jq .RunSSH
true            # SSH is on
```

Two vendor-blessed surfaces, opposite answers, and the naive read is a **false negative
in the unsafe direction**. `tsattest` uses the prefs field and prints the contradiction
alongside the verdict so the next person does not rediscover it.

## Why the third question is not a boolean

`tailscaled` runs as root and `/proc/<pid>/environ` is mode `0400 root:root`. From an
unprivileged account the loaded value **cannot be measured** - so the tool prints
`UNKNOWN` and names what would fix it, rather than inferring "not set" from a file, or
"set" from the file that was supposed to configure it. A PASS is only ever printed for a
value that was actually read.

## Usage

```
cd 2026-10-28-tsattest
PYTHONPATH=src python3 -m tsattest       # prose report
PYTHONPATH=src python3 -m tsattest --json    # machine-readable
sudo PYTHONPATH=src python3 -m tsattest     # measures the process env too
```

Exit codes (fail-closed, same contract as `kvpreflight`):

| code | meaning |
|---|---|
| `0` | `PASS` - nothing at or above threshold was found |
| `1` | `FAIL` - at least one bulletin applies and is open |
| `2` | `UNKNOWN` - could not answer; never collapsed into `0` |

`--strict` maps `UNKNOWN` to exit `1` for CI gates.

### Flags

| flag | effect |
|---|---|
| `--json` | emit JSON instead of prose |
| `--fixtures DIR` | read probe output from files instead of running `tailscale` (`version.txt`, `prefs.json`, `status.json`, `serve.txt`, `environ.txt`, `defaults.txt`) |
| `--tailscale-bin PATH` | alternate binary (default `tailscale`) |
| `--defaults-file PATH` | EnvironmentFile treated as *declared* (default `/etc/default/tailscaled`) |
| `--strict` | treat `UNKNOWN` as failure |

Fixture mode exists so the tool itself is testable without a tailnet, and so a report can
be reproduced from evidence captured on another host.

## What it prints

```
bulletins: 5 probed, 3 open, 0 closed, 2 not applicable, 0 unknown
probes: 6 probed, 5 measured, 1 unmeasurable
probe coverage: 5 of 6
```

The counts are load-bearing: a branch that was **never read** must not look like a branch
that was read and found clean. `probe coverage` states how many of the six surfaces
actually returned a value.

## The bulletin table

Hand-written, not a CVE feed - the vendor publishes about one bulletin a week, and
applicability (not existence) is the question.

| bulletin | fixed in | applies when |
|---|---|---|
| TS-2026-013 | 1.104.2 | always (system TLS trust store) |
| TS-2026-014 | 1.104.4 | Tailscale SSH enabled |
| TS-2026-015 | 1.104.4 | Tailscale SSH enabled |
| TS-2026-016 | 1.104.4 | a serve **unix-socket** backend exists |
| TS-2026-017 | 1.104.4 | serve over **TLS** with **>= 2 mounts** |

Source: <https://tailscale.com/security-bulletins> (read 2026-10-28). Version comparison is
per-bulletin, never against "latest": a host can be past `1.104.2` and short of `1.104.4`.

## Tests

Standard library only, no pytest:

```
cd 2026-10-28-tsattest
PYTHONPATH=src python3 -m unittest discover -s tests
```

## Scope

Local node only. No network calls, no CVE database, no ACL review, no package manager.
Zero runtime dependencies; Python 3.8+.
