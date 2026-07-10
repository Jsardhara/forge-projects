# AgentVault

**Secret-scoped execution layer for AI agents.** Zero external dependencies,
stdlib-only. Hand your coding/research agents *scoped, revocable, short-lived*
credentials instead of real secrets — and prove with a tamper-evident audit trail
that nothing was exfiltrated.

## Why

AI agents with repo/API access leak secrets (GitLost, Flint, Cloudflare Drop, the
agent-that-ran-a-$100M-fundraise story). AgentVault is the preventive control plane:

1. **Never hands out the real secret.** The vault stores `value`s; agents receive a
   *session token* and call `vault.resolve()` at use-time, after scope/expiry checks.
2. **Scoped, revocable, short-lived.** Each session has a TTL, an optional use-limit,
   a secret allowlist, and can be revoked instantly by the operator.
3. **Egress allowlist.** A default-deny egress gate blocks the agent from reaching any
   host not on its allowlist (wildcards + CIDR supported).
4. **Tamper-evident audit.** Every access decision (allow *and* deny) is appended to a
   SHA-256 hash-chained log. Any retroactive edit breaks the chain — verifiable proof.

## Install

```bash
pip install .
```

## Quick start (library)

```python
from datetime import timedelta
from agentvault import Vault, Scope, SecretKind

v = Vault()
key = v.add_secret("alpaca-key", "REAL_SECRET", kind=SecretKind.API_KEY,
                   allowed_hosts=("api.alpaca.markets",))
sess = v.issue_session(
    scope=Scope(secret_ids=(key.sid,), allowed_hosts=("api.alpaca.markets",),
                can_proxy_egress=True, max_uses=5),
    ttl=timedelta(minutes=15),
)

val = v.resolve(sess.session_id, key.sid)      # -> "REAL_SECRET"
v.check_egress(sess.session_id, "api.alpaca.markets", 443)  # -> True
v.check_egress(sess.session_id, "evil.com", 443)           # -> raises EgressDeniedError

v.revoke_session(sess.session_id)              # instant kill-switch
print("audit intact:", v.audit_verify())       # -> True
```

## CLI

```bash
agentvault demo                              # end-to-end walkthrough
agentvault secret add --name alpaca --value $KEY --kind api_key --host api.alpaca.markets
agentvault session issue --egress --ttl 30 --max-uses 3
agentvault egress check --host api.github.com --rules api.github.com  # ALLOW (rc 0)
agentvault audit
```

## How it differs from neighbors

- **vs `ai-agent-sandbox` / `agentos`** — those sandbox *execution*; AgentVault manages
  *credential lifecycle* + egress policy.
- **vs `mcp-shield`** — that is an MCP *tool-call* policy engine; AgentVault is a
  credential broker + egress proxy for the agent's own runtime scope.
- **vs `breach-sentinel`** — that detects breaches *after* the fact; AgentVault is
  *preventive* (secret is never exposed, egress is blocked).

## Tests

```bash
pytest tests/ -v
```

## License

MIT
