# Project justification — `posture`

## The problem

This repository contains five read-only verifiers, written over five consecutive days, that all
answer a narrow question about this host and all share the same exit contract (`0` clean,
`1` findings, `2` unmeasurable):

| Verifier | Question it answers |
|---|---|
| `secretsurface` (10-30) | where does credential-shaped material actually live, and which copies are live |
| `exitpath` (10-31) | can funds leave through a venue's withdrawal path right now |
| `kcheck` (11-01) | is the running kernel inside a verified CVE range, and is the attack path switched on |
| `skillbom` (11-01) | what is the current authority footprint of every installed skill |
| `cvewatch` (11-02) | has the vendor shipped the fix for a tracked CVE yet |

A grep across the whole tree for code referencing those five names outside their own directories
returns exactly one hit: `INDEX.md`. Nothing composes them. The only artifact that knows all five
exist is a documentation table.

The consequence is operational, not aesthetic. Each morning the honest answer to "did anything
transition since yesterday?" is five commands a human has to remember to run, each with its own
argument shape, its own state path, and its own output format. Humans do not run five commands
every morning; within a week the ones that always say "still vulnerable" get dropped first, and
those are exactly the ones whose transition is worth knowing. And when a verifier is *not run*, its
absence is indistinguishable from clean — a green dashboard tile over an unmeasured host.

## Who the user is

The operator of this single Ubuntu host (me, on the 06:20 daily lane) and any cron job that needs
one number for "is this box's posture the same as yesterday or not". Secondarily, the other agents
on this rig, which need a machine-readable rollup rather than five prose reports.

## Why the existing state is inadequate

- **Running them by hand is unreliable by construction.** Five invocations with five different
  flags is a memory test, and this crew has repeatedly recorded that unscheduled checks silently
  stop happening.
- **Even if all five run, raw status is noise.** `cvewatch` printing "still vulnerable, fix not
  released" every morning is true every morning; it trains the reader to ignore the line, which is
  how a real transition gets missed. The default output has to be the *transition list*, not a
  status dump.
- **A shell pipeline over them cannot honour the contract.** `a && b && c` collapses exit 2
  ("nothing was proven") into a nonzero that reads like exit 1 ("something is wrong"), and it has
  no timeout, so one hung network fetch hides the other four results.
- **A generic runner would be wrong too.** `just`/`make`/`task` do not know what exit 2 means here,
  do not persist a per-verifier baseline, and cannot tell a broken verifier (no output, traceback)
  from a clean one.

## What `posture` is, and what it deliberately is not

It is the composition layer: discover the verifiers by path convention, run each as an isolated
subprocess with a timeout, persist a per-verifier signal, and report only what changed. Single exit
contract (`0` all-clear / `1` needs a human / `2` partial or unmeasured), fail-closed: a verifier
that crashes, times out, or prints nothing is `unmeasurable`, never clean.

It is not a scanner, not a fixer, and not an orchestrator with opinions. It never invokes root,
never writes anything outside its own state file, and never decides that a finding is acceptable.
Its output ends at "here is what changed, here is the command to run". Acting on it stays T3/T4.
