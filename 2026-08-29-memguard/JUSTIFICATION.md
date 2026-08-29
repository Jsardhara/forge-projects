# Project Justification: memguard

**What real problem does this solve?**
AI agents (including the Jarmes multi-agent system itself) persist goals, context, and
preferences in memory and prompt files — `MEMORY.md`, `LEARNINGS.md`, system prompts, skill
knowledge bases. These files are written by code, other agents, and external tooling, often
with little scrutiny. The OWASP "Top 10 for Agentic Applications 2026" explicitly names
**memory poisoning** and **goal hijacking** as top-threat classes: an attacker who can inject
instruction-like text into a file the agent reads later (a poisoned web scrap retold into
memory, a malicious tool-write, a crafted chunk in a retrieval store) steers the agent's
decisions — changing its true goal, asking it to exfiltrate secrets, escalate privileges,
or ignore its guardrails.

**Who is the user?**
Anyone operating a persistent-memory agent: the operator of this multi-agent system, teams
running coding agents with long-lived memory, and developers shipping agent skills/prompts.

**Why are existing solutions inadequate?**
SaaS "prompt-injection" detectors require sending your memory content to a third-party API —
a non-starter for the very files most likely to hold secrets. Runtime tool-call governors
(AgentVault, MCP Shield in this repo) police *execution*, but nothing in the portfolio
statically inspects the *memory/prompt layer* the agent trusts on read. memguard fills that
gap: a zero-dependency, offline, no-LLM static scanner that flags instruction-vs-data
confusion, role-override, exfiltration, credential-harvest, privilege-escalation, obfuscation,
and authority-fabrication signals in any file an agent will load as context.

**How will we know it succeeds?**
Clean scans return no findings (no false positives on benign memory files); poisoned fixtures
are detected with correct severity + exit code in CI gate; and the tool scans this system's
own memory files cleanly while flagging a deliberately-injected example.