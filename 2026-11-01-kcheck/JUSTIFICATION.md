# Project justification — `kcheck`

## The real problem

On 2026-10-15 NVD published **CVE-2026-98432**, a use-after-free in the Linux IPv4 TCP
handshake reachable on the MPTCP path: **CVSS 3.1 9.8, `AV:N/AC:L/PR:N/UI:N`** — remote,
no credentials, no user interaction. A published PoC reportedly reached **root command
execution with no credentials** on a host with an MPTCP listener. Fixed upstream in
5.10.272 / 6.1.190 / 6.6.159 / 6.12.113 / 6.18.56 / 7.2.10 / 7.3.

On 2026-11-01 the host this project was built on — Ubuntu 26.04.1 LTS, kernel
`7.0.0-38-generic` — was **in range**, with Ubuntu's fix (`7.0.0-43.43`) *not yet
released*. Five ABI levels short of an unfixed remote kernel bug, with MPTCP enabled and
five MPTCP listeners live on the tailnet.

That is the problem in one sentence: **the CVE feed tells you the bug is bad; nothing
tells you whether your kernel is below the fix and whether the path exists on your box.**

## Who the user is

The operator of a handful of Linux boxes — a dev rig, a home server, a small fleet —
who reads a CVE advisory and has to answer, immediately: *does this apply to me, right
now, before I reboot into something else?* Today that answer is assembled by hand:
`uname -r`, then a version comparison in your head against a package version with an ABI
suffix, then a distro tracker page, then `ss`/`sysctl` to see whether the feature is even
on. Four sources, one wrong number, and a 9.8 filed as "probably fine".

## Why existing solutions are inadequate

- **CVE feeds and vulnerability scanners** (NVD, OSV, Trivy, `debsecan`) answer "is this
  package name in a list". They do not separate *distro has not released a fix* from
  *distro has not fixed it yet and you are exposed now* — and `7.0.0-38` vs `7.0.0-43.43`
  is exactly the comparison where a naive one gets the sign wrong.
- **Package managers** (`unattended-upgrades`, `dnf-automatic`) answer "is there an
  update to install", which is empty advice when the fix is still `work in progress`.
  Exit code 2 is the honest answer and no package manager gives it.
- **General vulnerability scanners** report package CVE status and stop there. The CVE's
  demonstrated path here is a *listener* — a host can be in range and unreachable, or
  patched and still listening. Two axes, two booleans, no scanner merges them.
- **Doing it by hand** is what was actually done on 2026-11-01 to establish the facts this
  tool encodes. Doing it by hand again next week is how the fact goes stale silently.

## The specific gap this closes

The daily pipeline deferred this build because the affected/fixed range was unverified at
06:20Z — correctly, since an unverified range is exactly the state in which a scanner
should refuse to answer. The range was verified at 06:26Z, six minutes after the slot
closed. `kcheck` is that verification made executable and re-runnable, with the table's
provenance checked in alongside it so the *next* stale fact is visible rather than
silent.

## Why this implementation, and not another

- **Version comparison is dpkg's algorithm, not a string compare.** This is the single
  highest-risk line of code in the project; it is ported literally and pinned by a
  boundary table.
- **Exit 2 exists and is mandatory** whenever the fixed version for the running distro is
  unknown. A tool that says "not vulnerable" without data is worse than no tool.
- **`fix_pending` is modelled as its own state** because "vendor confirmed, fix not
  released" is the state this host is actually in, and collapsing it into either
  "vulnerable" or "fixed" produces a false statement either way.
- **The two axes are separate.** In range with no listener is still in range.
- **No host mutation.** The mitigation is an operator decision; a checker that writes an
  nftables rule is an outage generator. It prints a pointer.
- **Offline, stdlib only, no root.** It runs in under 100 ms on a cold start, so it can
  run every boot without anyone noticing — which is the only way it gets used.

## What it would take to be wrong

- The table's `retrieved_at` ages past seven days and nobody re-verifies it. The tool says
  `STALE` and exits on the verdict anyway — provenance is visible, not enforced.
- A distro backports the fix into a lower ABI (Ubuntu routinely does). The table stores
  an explicit `fixed_version` per distro row precisely so a backport can be recorded as
  the real fix rather than inferred from the upstream train.
- The demonstrated path changes shape. `attack_path.probe` is per-row data, so a new one
  is a table edit plus one probe, not a rewrite.
