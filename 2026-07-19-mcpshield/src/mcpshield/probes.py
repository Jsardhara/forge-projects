"""mcpshield probe engine.

Each probe inspects an MCPServerSpec and yields zero or more Findings. The probes
model the failure modes observed in the 2026 MCP health-check studies:
- dangerous/unbounded tools (exec, shell, write, delete)
- unbounded egress (wildcard / internal exfil)
- hardcoded or unscoped secrets
- missing capability annotations (undeclared intent)
- prompt-injection surface
- unencrypted / unauthenticated remote transports
- over-provisioned (least-privilege) declarations
"""
from __future__ import annotations

import re
from typing import List

from mcpshield.models import (
    EgressRule,
    Finding,
    MCPServerSpec,
    PromptSpec,
    SecretRef,
    ToolSpec,
)

# Tokens that indicate a destructive / privileged capability.
DESTRUCTIVE_TOKENS = {
    "exec", "execute", "shell", "bash", "cmd", "command", "run", "system",
    "eval", "spawn", "process", "popen", "subprocess", "pipe", "write",
 "delete", "remove", "rm", "mv", "cp", "upload", "kill", "chmod", "chown",
 "truncate", "drop", "shutdown", "reboot",
 }
# Tokens that indicate arbitrary network egress.
NETWORK_TOKENS = {
    "fetch", "curl", "wget", "download", "request", "scrape", "http", "call",
    "invoke", "post", "get_", "send",
}
# Calm-claim phrases that, paired with a dangerous tool name, indicate a
# deceptive / mismatched declaration.
CALM_CLAIM_RE = re.compile(
    r"\b(no|not|never|doesn'?t|won'?t|cannot|can'?t|safe|read[- ]?only|"
    r"without (execution|writing)|read only|read-only)\b",
    re.IGNORECASE,
)
# Prompt-injection directive language.
INJECTION_DIRECTIVE_RE = re.compile(
    r"\b(ignore (previous|prior|all)|system prompt|you are now|disregard|"
    r"override|new instructions|forget (everything|previous))\b",
    re.IGNORECASE,
)
# Private / internal IP ranges that signal potential internal exfiltration.
_PRIVATE_PREFIXES = ("10.", "192.168.", "172.16.", "172.17.", "172.18.", "172.19.",
                     "172.2", "172.30.", "172.31.", "127.", "localhost", "169.254.")


def _tokens(name: str) -> set:
    return {t for t in re.split(r"[^a-z0-9_]+", (name or "").lower()) if t}


def _is_private_dest(dest: str) -> bool:
    d = (dest or "").lower()
    if d.startswith("http://"):
        d = d[len("http://"):]
    elif d.startswith("https://"):
        d = d[len("https://"):]
    d = d.split("/")[0].split(":")[0]
    if d in ("localhost", "0.0.0.0", "::1"):
        return True
    return any(d.startswith(p) for p in _PRIVATE_PREFIXES)


def _is_wildcard(dest: str) -> bool:
    d = (dest or "").strip().lower()
    return d in {"*", "any", "0.0.0.0", "0.0.0.0/0", "::", "internet", "all", ""}


def classify_tool(tool: ToolSpec):
    """Return (has_destructive, has_network, open_world, read_only)."""
    toks = _tokens(tool.name) | _tokens(tool.description)
    ann = tool.annotations or {}
    open_world = ann.get("openWorldHint")
    read_only = ann.get("readOnlyHint")
    return (
        bool(DESTRUCTIVE_TOKENS & toks),
        bool(NETWORK_TOKENS & toks),
        open_world,
        read_only,
    )


# --------------------------------------------------------------------------
# Probes
# --------------------------------------------------------------------------
def probe_tool_allowlist(spec: MCPServerSpec) -> List[Finding]:
    out: List[Finding] = []
    if not spec.tools:
        out.append(Finding(
            probe="tool_allowlist", severity="MEDIUM",
            title="No tools declared",
            detail="The server exposes zero tools. This is either a misconfiguration "
                   "or a server that accepts connections without providing any "
                   "verifiable capability surface.",
            recommendation="Declare the tools the server actually provides, or treat "
                          "an empty tool surface as untrusted.",
        ))
        return out

    for tool in spec.tools:
        has_d, has_n, open_world, read_only = classify_tool(tool)
        calm = bool(CALM_CLAIM_RE.search(tool.description or ""))

        if has_d:
            # Deceptive declaration: dangerous name but description claims otherwise.
            if calm:
                out.append(Finding(
                    probe="tool_allowlist", severity="HIGH",
                    title=f"Deceptive tool declaration: '{tool.name}'",
                    detail=f"Tool name implies a privileged/destructive capability but "
                           f"description claims the opposite: \"{tool.description}\". "
                           f"Agents cannot rely on the description to constrain behavior.",
                    recommendation="Align the description with the tool's real behavior "
                                   "or remove the capability.",
                ))
            if open_world is True:
                out.append(Finding(
                    probe="tool_allowlist", severity="CRITICAL",
                    title=f"Destructive + open-world tool: '{tool.name}'",
                    detail="Tool can mutate external state (exec/write/delete/etc.) AND "
                           "is declared open-world, meaning it can reach arbitrary "
                           "resources. This is the highest-risk tool shape.",
                    recommendation="Constrain the tool to a closed, allowlisted scope and "
                                   "require explicit human approval before invocation.",
                ))
            elif open_world is None:
                out.append(Finding(
                    probe="tool_allowlist", severity="HIGH",
                    title=f"Destructive tool with undeclared scope: '{tool.name}'",
                    detail="Tool implies a privileged/destructive capability but declares "
                           "no openWorldHint, so its blast radius is unknown.",
                    recommendation="Declare openWorldHint=false and constrain inputs, or "
                                   "justify open-world access explicitly.",
                ))
            else:  # open_world is False -> sandboxed
                out.append(Finding(
                    probe="tool_allowlist", severity="MEDIUM",
                    title=f"Destructive-but-sandboxed tool: '{tool.name}'",
                    detail="Tool implies a privileged capability but is declared "
                           "closed-world. Acceptable only if inputs are strictly constrained.",
                    recommendation="Verify the tool enforces its declared closed-world "
                                   "boundary at runtime, not just in metadata.",
                ))

        if has_n and open_world is True:
            out.append(Finding(
                probe="tool_allowlist", severity="HIGH",
                title=f"Network tool with open-world egress: '{tool.name}'",
                detail="Tool can make arbitrary network calls (fetch/curl/request) and is "
                       "declared open-world. Combined with agent context this enables "
                       "data exfiltration or SSRF.",
                recommendation="Restrict the tool to an explicit egress allowlist.",
            ))
    return out


def probe_egress_scope(spec: MCPServerSpec) -> List[Finding]:
    out: List[Finding] = []
    net_tools = [t for t in spec.tools if classify_tool(t)[1]]
    for e in spec.egress:
        if _is_wildcard(e.dest):
            out.append(Finding(
                probe="egress_scope", severity="CRITICAL",
                title=f"Unbounded egress: '{e.dest}'",
                detail="Egress rule allows arbitrary destinations. An agent using this "
                       "server can exfiltrate data or reach attacker infrastructure.",
                recommendation="Replace the wildcard with a specific host/URL allowlist.",
            ))
        elif _is_private_dest(e.dest):
            out.append(Finding(
                probe="egress_scope", severity="MEDIUM",
                title=f"Egress to internal/loopback: '{e.dest}'",
                detail="Egress targets an internal or loopback address, which can be used "
                       "to pivot into internal services or exfiltrate to localhost proxies.",
                recommendation="Justify the internal destination or remove the rule.",
            ))
    if net_tools and not spec.egress:
        out.append(Finding(
            probe="egress_scope", severity="LOW",
            title="Network tools without declared egress scope",
            detail=f"{len(net_tools)} tool(s) imply network access but no egress scope is "
                   "declared, so the actual reachable destinations are unverifiable.",
            recommendation="Declare an explicit egress allowlist for network-capable tools.",
        ))
    return out


def probe_secrets_scoping(spec: MCPServerSpec) -> List[Finding]:
    out: List[Finding] = []
    declared_tools = {t.name for t in spec.tools}
    for s in spec.secrets:
        if s.source == "hardcoded":
            out.append(Finding(
                probe="secrets_scoping", severity="CRITICAL",
                title=f"Hardcoded secret: '{s.name}'",
                detail="A secret is embedded directly in the server spec rather than "
                       "referenced from an environment/secret store. It will be committed "
                       "and leaked.",
                recommendation="Move the secret to an env var or secret manager; rotate it.",
            ))
        if not s.scoped:
            out.append(Finding(
                probe="secrets_scoping", severity="MEDIUM",
                title=f"Broad/unscoped secret: '{s.name}'",
                detail="A single generic secret is declared without scoping to specific "
                       "tools/uses, violating least privilege.",
                recommendation="Scope the secret to the minimal set of tools that need it.",
            ))
        if s.used_by and spec.tools:
            used = set(s.used_by)
            if not (used & declared_tools):
                out.append(Finding(
                    probe="secrets_scoping", severity="LOW",
                    title=f"Secret unused by any declared tool: '{s.name}'",
                    detail="The secret declares usage by tools that are not present in the "
                           "server's tool list, suggesting over-provisioning or drift.",
                    recommendation="Remove the unused secret reference or align used_by "
                                   "with the declared tools.",
                ))
    return out


def probe_annotation_compliance(spec: MCPServerSpec) -> List[Finding]:
    out: List[Finding] = []
    for tool in spec.tools:
        has_d, _has_n, open_world, read_only = classify_tool(tool)
        if not tool.annotations:
            out.append(Finding(
                probe="annotation_compliance", severity="MEDIUM",
                title=f"Tool declares no MCP annotations: '{tool.name}'",
                detail="Without readOnlyHint/destructiveHint/openWorldHint the tool's "
                       "intent is undeclared, so an agent cannot apply policy safely.",
                recommendation="Add MCP annotations describing the tool's side effects.",
            ))
            continue
        if read_only is True and has_d:
            out.append(Finding(
                probe="annotation_compliance", severity="HIGH",
                title=f"Annotation/name mismatch: '{tool.name}' claims read-only",
                detail="Tool name implies a destructive/privileged capability but "
                       "readOnlyHint is true. Metadata contradicts behavior.",
                recommendation="Correct the annotation or rename the tool to match intent.",
            ))
        if tool.annotations.get("destructiveHint") is True and open_world is True:
            out.append(Finding(
                probe="annotation_compliance", severity="HIGH",
                title=f"Destructive + open-world annotation: '{tool.name}'",
                detail="Tool is annotated both destructive AND open-world — maximal blast "
                       "radius by its own declaration.",
                recommendation="Constrain the tool or require explicit approval.",
            ))
    return out


def probe_prompt_injection(spec: MCPServerSpec) -> List[Finding]:
    out: List[Finding] = []
    for p in spec.prompts:
        has_input = "{{" in p.template or "{" in p.template
        if p.trusted and has_input:
            out.append(Finding(
                probe="prompt_injection", severity="MEDIUM",
                title=f"Trusted prompt ingests external input: '{p.name}'",
                detail="A prompt marked trusted accepts external/placeholder input, which "
                       "is a classic injection surface: untrusted data becomes trusted "
                       "instruction.",
                recommendation="Do not mark prompts that ingest external input as trusted, "
                               "or sanitize/quote the input.",
            ))
        if INJECTION_DIRECTIVE_RE.search(p.template or ""):
            out.append(Finding(
                probe="prompt_injection", severity="LOW",
                title=f"Prompt template contains directive language: '{p.name}'",
                detail="Template includes instruction-override phrasing that could be "
                       "abused if external input is concatenated into it.",
                recommendation="Avoid embedding override directives in templates that take "
                               "external input.",
            ))
    return out


def probe_transport_security(spec: MCPServerSpec) -> List[Finding]:
    out: List[Finding] = []
    if spec.transport in ("http", "sse"):
        if not spec.tls:
            out.append(Finding(
                probe="transport_security", severity="HIGH",
                title=f"Unencrypted transport: {spec.transport}",
                detail="Remote transport is not TLS-terminated; traffic (including tool "
                       "arguments and secrets) is exposed on the wire.",
                recommendation="Enable TLS for the remote endpoint.",
            ))
        if not spec.auth:
            out.append(Finding(
                probe="transport_security", severity="MEDIUM",
                title=f"No auth on remote transport: {spec.transport}",
                detail="Remote transport has no authentication, allowing anyone who can "
                       "reach it to invoke tools.",
                recommendation="Require an auth token / mTLS on the endpoint.",
            ))
    else:  # stdio
        out.append(Finding(
            probe="transport_security", severity="INFO",
            title="stdio transport",
            detail="Local stdio transport keeps the server process-scoped; lower network "
                   "exposure than a remote endpoint.",
            recommendation="Still apply tool/secret scoping — stdio does not imply trust.",
        ))
    return out


def probe_least_privilege(spec: MCPServerSpec) -> List[Finding]:
    out: List[Finding] = []
    if not spec.tools and (spec.secrets or spec.egress):
        out.append(Finding(
            probe="least_privilege", severity="LOW",
            title="Capabilities declared without any tools",
            detail="The server declares secrets/egress but exposes no tools, suggesting "
                   "over-provisioned or dead configuration.",
            recommendation="Remove unused capability declarations.",
        ))
    return out


ALL_PROBES = [
    probe_tool_allowlist,
    probe_egress_scope,
    probe_secrets_scoping,
    probe_annotation_compliance,
    probe_prompt_injection,
    probe_transport_security,
    probe_least_privilege,
]


def run_probes(spec: MCPServerSpec) -> List[Finding]:
    findings: List[Finding] = []
    for probe in ALL_PROBES:
        findings.extend(probe(spec))
    return findings
