# Project Justification — plugattest

## The real problem

Four plugin and skill marketplaces are trending in the same week with no provenance or
capability disclosure at all: `anthropics/claude-plugins-official` (43,955 stars),
`anthropics/knowledge-work-plugins` (31,762), `cursor/plugins` (13,659), and
`android/skills`. A plugin or skill is not a passive file: it ships instructions an agent
will obey and, often, scripts that run with the agent's own privileges — the agent's API
keys, its filesystem, its network egress, its shell.

The install decision today is made from a manifest the publisher wrote. Nothing compares
that claim against what the code actually does. LiteLLM 1.107.0 is the concrete case of
why this matters: upstream GitHub source was clean, every published wheel was poisoned,
and the payload fired on any Python process start. `pubgate` (2026-10-23) answers "is this
artifact byte-identical to what upstream built" for wheels. It does not answer the
question a plugin install actually poses: **does the shipped code exercise capabilities
the manifest never declared?**

## Who the user is

Two users, one tool:

1. **A developer or ops engineer who installs agent plugins/skills into a shared
   environment** (Hermes, Claude Code, Cursor) and must decide, per package, whether to
   trust it. They want a gate they can run in pre-commit or CI that fails closed.
2. **A publisher** who wants to prove their package stays inside the capability envelope
   they advertised — the same artifact, attested by the buyer rather than promised by the
   seller.

## Why existing solutions are inadequate

- **Runtime sandboxes** (e.g. NVIDIA/OpenShell, shipped 2026-10-23) govern what a process
  may do *while it runs*. They do not tell you what the package *intended* to do, and they
  cannot fail an install before the code ever executes.
- **Static "security audit" skills** (cloudflare/security-audit-skill, 40,055 stars) are
  general code review driven by an LLM: non-deterministic, no manifest baseline, no
  exit code a CI can gate on.
- **Package-manager provenance** (attestations, sigstore) proves *who published* an
  artifact, not *what capabilities it uses*. A signed package that silently reads
  `~/.ssh/id_rsa` is a trusted-signature, undeclared-capability package.
- **`pubgate`** verifies wheel integrity against upstream source. It is the supply-chain
  half; it has no notion of declared capabilities, plugin manifests, or skill frontmatter.

None of these produces the one comparison this tool produces: declared capability set
(what the manifest says) versus detected capability set (what the code does), per file,
with a fail-closed verdict.

## Scope

Deterministic, offline, zero dependencies, standard library only. It parses the manifest
forms that actually ship in these marketplaces (`package.json`, `plugin.json`, and
`SKILL.md` frontmatter), scans the package's own source files for capability signals, and
reports undeclared capability use, declared-but-unused capability, and auto-execution
hooks as severity-ranked findings with a CI exit code.
