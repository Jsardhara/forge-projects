# mcpshield

**Secure MCP server health-check & sandbox policy engine.**

A zero-dependency, stdlib-only analyzer that pre-flights an MCP (Model Context
Protocol) server *specification* — its declared tools, egress, secrets,
prompts, and transport — and returns a **PASS / WARN / FAIL** verdict with a
0-100 risk score and per-probe reasoning. Designed to run as a CI gate or a
manual review signal **before** an agent is allowed to trust an MCP server.

> Why: a 2026 MCP health-check study ran 79 MCP servers in microVMs and only
> **31 (39%) passed** — the failures were about tool allowlists, unbounded
> egress, unscoped secrets, and missing capability annotations. `mcpshield`
> catches exactly those failure modes statically, in seconds, with no infra.

## How this differs from `mcp-shield` (2026-06-19)

The forge-projects repo already contains **`mcp-shield`**, but the two tools
operate at different layers and are complementary, not duplicate:

| | `mcp-shield` (2026-06-19) | `mcpshield` (this project) |
|---|---|---|
| Stage | **Runtime** — sits between agent and server | **Pre-flight** — before the server is wired in |
| Input | Live tool-call context (agent, tool, args) | Declared server *spec* (tools, egress, secrets, prompts, transport) |
| Job | Allow/deny each call, rate-limit, audit-log, compliance report | PASS/WARN/FAIL health verdict + 0-100 risk score |
| Analogy | A firewall + SIEM on the wire | A security review of the blueprint |

Use `mcpshield` to decide whether to *trust* a server at all; use `mcp-shield`
to govern it *while it runs*.

## Install

```bash
pip install .
```

(No third-party dependencies — pure Python standard library, Python >= 3.10.)

## Usage

```bash
# Analyze a single server spec
mcpshield check server.json

# JSON output (for piping into CI / dashboards)
mcpshield check server.json --json

# Batch-scan every *.json in a directory
mcpshield check --dir ./mcp-servers

# Version
mcpshield version
```

Exit code is **1 when any analyzed server FAILs** (so it works as a CI gate),
**0** otherwise, **2** on usage error.

### Spec format

A spec is a JSON document describing the server:

```json
{
  "name": "my-server",
  "transport": "stdio",
  "auth": false,
  "tls": false,
  "tools": [
    {
      "name": "fetch_docs",
      "description": "Fetch documentation from the docs API.",
      "annotations": { "readOnlyHint": true, "openWorldHint": false }
    }
  ],
  "egress": [ { "dest": "https://docs.example.com", "scope": "specific" } ],
  "secrets": [ { "name": "DOCS_TOKEN", "source": "env:DOCS_TOKEN", "scoped": true } ],
  "prompts": []
}
```

A file may also be a list of specs, or `{"servers": [ ... ]}`.

## Probes

| Probe | Catches |
|-------|---------|
| `tool_allowlist` | Destructive + open-world tools, deceptive name/description mismatches, empty tool surfaces |
| `egress_scope` | Wildcard/unbounded egress, exfiltration to internal/loopback addresses |
| `secrets_scoping` | Hardcoded secrets, broad/unscoped tokens, unused secret declarations |
| `annotation_compliance` | Missing MCP annotations, read-only claims on destructive tools |
| `prompt_injection` | Trusted prompts that ingest external input, override-directive templates |
| `transport_security` | Unencrypted / unauthenticated remote (http/sse) transports |
| `least_privilege` | Over-provisioned capabilities with no backing tools |

## Scoring

`risk_score` = sum of severity weights (`CRITICAL` 25, `HIGH` 12, `MEDIUM` 5,
`LOW` 2, `INFO` 0), capped at 100. Band: **FAIL** if any `CRITICAL` or
score >= 50; **WARN** if any `HIGH` or score >= 20; otherwise **PASS**.

## Library use

```python
from mcpshield import spec_from_dict, analyze

spec = spec_from_dict(json.load(open("server.json")))
report = analyze(spec)
print(report.band, report.risk_score)
```

## Tests

```bash
pytest tests/ -v
```

## License

MIT
