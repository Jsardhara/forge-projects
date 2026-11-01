# Project justification - `skillbom`

## The real problem

A Hermes host loads skills the way an operating system loads drivers: with the host's own
authority. On this machine that is 9 profiles holding 544 `SKILL.md` files and roughly 580
script files, and not one of those numbers is visible to the person who owns the machine
until someone counts them by hand. A skill is not documentation. It ships instruction text
an agent obeys and, frequently, scripts that run with the agent's shell, network, home
directory, and environment - including whatever credentials are in it. Installing one is a
decision to grant authority, and today that decision is made from a description field.

The measurable part of this is not a vulnerability; it is an **inventory gap**. There is no
answer to "what can the skills on this host do, where do those skills come from, and which
copies of the same skill have drifted apart?" A crew that cannot answer that cannot audit
its own authority, and every new skill makes the blind spot larger and cheaper to ignore.

## Who the user is

The operator of a multi-profile agent host - the person who installed 61 skills nine times
over, who wants to know which of those copies differ, which skills reach the network, and
which ones read `~/.hermes` or `.env`. Secondary user: any team reviewing a skill pack
before rollout, where "what does this actually do" has to be answered by something other
than the publisher's own summary.

## Why existing solutions are inadequate

- `plugattest` (built here, 2026-10-24) answers a **different question**: for one package,
  does its manifest claim match its code? It emits a per-artifact FLAG/PASS verdict and
  knows nothing about a fleet, duplication, or drift over time. Running it over a
  marketplace answers "is each package honest", not "what authority does this host hold".
- `secretsurface` (2026-10-30) inventories **credential material**, deliberately stopping
  at values. A skill can reach the network and write outside its profile without ever
  touching a credential-shaped string, so it is invisible to a secret scan.
- Package managers (`pip list`, `npm ls`) list installed artifacts and their versions.
  Skills are not packages: they have no registry, no lockfile, no dependency graph, and no
  version that reflects their content. Two profiles can hold the same skill name at
  different content with no signal anywhere.
- Reading the directory by hand is exactly the method that has already produced
  contradictory counts in this project's own history.

## What this build is, narrowly

A read-only capability ledger: one record per installed skill (profile, name, path,
`SKILL.md` hash, declared tools, script list with per-script content hashes and static
capability signals), a fleet rollup of which skills are duplicated or diverged across
profiles, and a diff against the previous ledger so drift is a measurement rather than a
recollection. It never executes a skill script, never reads a credential value, and never
touches the network. Where it cannot measure - a missing root, an unreadable file, a
`SKILL.md` whose frontmatter will not parse - it says so and exits non-zero rather than
reporting a clean nothing.
