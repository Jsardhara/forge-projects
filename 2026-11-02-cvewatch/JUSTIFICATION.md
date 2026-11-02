# Project Justification — `cvewatch`

**The problem.** A CVSS 9.8 vulnerability (CVE-2026-98432, Linux IPv4/TCP use-after-free on
the MPTCP path, remote and unauthenticated) is live on this host right now. The fix does not
exist yet: Ubuntu's tracker lists `7.0.0-43.43` as the *target* version for 26.04 LTS, "work in
progress", not a released package. This host runs `7.0.0-38.38` — five ABI levels short. For as
long as the fix is pending, the only question that matters is not "am I in the range?" but "when
do I get out?" — and today the only thing answering it is a person refreshing a web page.

**Who the user is.** The operator of this rig, and the agent fleet that runs on it. Every daily
build, sweep, and cron here runs as an unprivileged user on a kernel that cannot be patched by an
agent: the kernel upgrade itself is operator-only (T4). So the machine's job is to notice the
transition — fix released, or kernel changed under it — and say so once, loudly, without needing
root and without becoming a daily "still vulnerable" alarm that gets tuned out.

**Why existing solutions are inadequate.** `kcheck` (built here 2026-11-01) answers the one-time
question with a *checked-in static table*: it cannot see a fix ship, and it has no watch mode
(grepped: 0 `watch` hits in its sources). NVD gives a CVSS score and an abstract version range, not
this distro's per-release package rows. `apt`/`unattended-upgrades` act on packages that already
exist — they cannot report "the fix for this CVE is still not built upstream". The Ubuntu CVE page
is authoritative and machine-readable in principle, but only as HTML: 1,353 table rows for this CVE
alone across 169 source packages. Reading it by hand is how the one fact that matters gets missed.
A watcher that fetches that page, parses the per-release rows with a real dpkg version compare,
compares against the installed kernels, and diffs against the previous run's saved state closes the
gap — and it is the transition, not the steady state, that it reports.
