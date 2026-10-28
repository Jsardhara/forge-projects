# Project Justification - tsattest

**The problem.** On 2026-10-26/27 Tailscale published five security bulletins
(TS-2026-013 through TS-2026-017) against its client, with fixes split across 1.104.2
and 1.104.4. An operator reading any of the usual "am I affected?" surfaces gets a
different answer from each: package managers report a version, `tailscale status --json`
reports a `Self.SSH_HostKeys` field, `tailscale debug prefs` reports `RunSSH`, and the
environment variable that actually mitigates the SSH-only bulletins
(`TS_SSH_DISABLE_FORWARDING`) exists in a config file *and*, separately, in the running
process's memory. These are not four views of one fact. On this host the two vendor
surfaces disagree right now: `Self.SSH_HostKeys` is `null` (which reads as "Tailscale SSH
is off") while `debug prefs` says `RunSSH: true` in the same minute. The naive reading is
a false negative in the unsafe direction - it reports the host as less exposed than it is.

**Who the user is.** The person who owns that node: an admin with SSH enabled, `serve`
in use, and no root shell in the monitoring path. `tailscaled` runs as root and its
`/proc/<pid>/environ` is mode `0400 root:root` - so the *actual* mitigation state is one
of the things they cannot read from the account they monitor from. The tool must be
useful from that unprivileged seat, which means its most valuable output is often "I
could not measure this, and here is exactly what would let me."

**Why existing solutions are inadequate.** A CVE feed tells you that you are behind, not
which of five bulletins apply to *your* configuration - applicability depends on `serve`
mounts, on whether SSH is on, and on whether a serve backend is a unix socket. A version
checker collapses the three-way split (declared in config / loaded in the process /
unmeasurable without root) into a single boolean, and the collapse always lands on the
optimistic side. That is precisely the failure mode Cloudflare described in its own
post-mortem of a config-vs-runtime gap. `tsattest` is the small tool that refuses to make
that collapse: it reports the vendor surfaces side by side, marks every unreadable value
`UNKNOWN` with the reason and the flag that would fix it, and will only print `PASS` when
the value it is passing on was read from the running process - never inferred from the
file that was supposed to configure it.

**Scope discipline.** Local node only. No CVE feed, no network calls, no ACL linting, no
scanner database - the vendor publishes roughly one bulletin a week, so a hand-written
`(bulletin, fixed_in)` table is the correct data structure, not a compromise.
