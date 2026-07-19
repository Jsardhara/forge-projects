# Project Justification — mcpshield

## Problem
MCP (Model Context Protocol) servers are rapidly becoming the integration layer
between LLM agents and the outside world — file systems, shells, APIs, databases.
The 2026-07-19 Lens intel surfaced a concrete, live gap: a microVM sandbox study
ran **79 MCP servers and only 31 (39%) passed** health checks
(Show HN / usethrone.dev + MCP Census of 15,382 servers). The failures were about
tool allowlists, unbounded egress, unscoped secrets, and missing capability
annotations. There is no lightweight, dependency-free way for an agent operator to
*pre-flight* an MCP server spec and get a pass/fail verdict with reasons before
trusting it inside an agent runtime.

## User
Agent builders and platform engineers who run MCP servers (e.g. the Jarmes system
itself runs remote-desktop + native-mcp servers). Anyone wiring an MCP server into
an autonomous agent loop who needs a CI gate or manual review signal.

## Why existing solutions are inadequate
- Real sandboxing (Firecracker/gVisor microVMs) is infrastructure-heavy (3-4 week
  build, Go, privileged hosts) — overkill for a *static pre-flight check*.
- MCP SDKs validate schema, not *security posture*.
- No stdlib, zero-dependency analyzer exists that an agent can run locally in
  seconds as a gate.

## Success criteria
- A single CLI `mcpshield check <spec.json>` produces a structured PASS/WARN/FAIL
  report with a 0-100 risk score and per-probe reasoning.
- Exit code 1 on FAIL so it works as a CI gate.
- Zero third-party dependencies (stdlib only) so it runs anywhere an agent runs.
- Covered by a green test suite that proves each probe fires on a crafted-bad spec
  and stays quiet on a crafted-good spec.
