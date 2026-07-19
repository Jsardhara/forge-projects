from mcpshield.probes import (probe_egress_scope, probe_secrets_scoping,
                             probe_tool_allowlist, probe_annotation_compliance,
                             probe_prompt_injection, probe_transport_security,
                             probe_least_privilege, run_probes)
from mcpshield.models import MCPServerSpec
from fixtures import (good_spec, bad_spec, deceptive_tool_spec,
                     honest_destructive_spec)


def _sev(probe_fn, spec, sev):
    return [f for f in probe_fn(spec) if f.severity == sev]


# ---- tool_allowlist -------------------------------------------------------
def test_destructive_openworld_is_critical():
    fs = [f for f in probe_tool_allowlist(bad_spec()) if "run_shell_command" in f.title]
    assert any(f.severity == "CRITICAL" for f in fs)


def test_deceptive_tool_flagged_high_not_critical():
    fs = probe_tool_allowlist(deceptive_tool_spec())
    titles = [f.title for f in fs]
    assert any("Deceptive" in t for t in titles)
    # openWorldHint is False here, so it must NOT be the open-world CRITICAL
    assert not any(f.severity == "CRITICAL" for f in fs)


def test_honest_destructive_undeclared_scope_high():
    fs = probe_tool_allowlist(honest_destructive_spec())
    assert any(f.severity == "HIGH" and "undeclared scope" in f.title for f in fs)


def test_empty_tools_medium():
    spec = MCPServerSpec.from_dict({"name": "empty"})
    fs = probe_tool_allowlist(spec)
    assert any(f.severity == "MEDIUM" and "No tools" in f.title for f in fs)


# ---- egress_scope ---------------------------------------------------------
def test_wildcard_egress_critical():
    fs = probe_egress_scope(bad_spec())
    assert any(f.severity == "CRITICAL" and "Unbounded egress" in f.title for f in fs)


def test_private_egress_medium():
    fs = probe_egress_scope(bad_spec())
    assert any(f.severity == "MEDIUM" and "internal/loopback" in f.title for f in fs)


def test_network_tools_no_egress_low():
    spec = MCPServerSpec.from_dict({
        "name": "n", "tools": [{"name": "fetch_url", "description": "fetch a url"}]
    })
    fs = probe_egress_scope(spec)
    assert any(f.severity == "LOW" and "without declared egress" in f.title for f in fs)


# ---- secrets_scoping ------------------------------------------------------
def test_hardcoded_secret_critical():
    fs = probe_secrets_scoping(bad_spec())
    assert any(f.severity == "CRITICAL" and "Hardcoded secret" in f.title for f in fs)


def test_unscoped_secret_medium():
    fs = probe_secrets_scoping(bad_spec())
    assert any(f.severity == "MEDIUM" and "unscoped" in f.title.lower() for f in fs)


def test_unused_secret_low():
    spec = MCPServerSpec.from_dict({
        "name": "n",
        "tools": [{"name": "search", "description": "search"}],
        "secrets": [{"name": "K", "source": "env:K", "scoped": True,
                     "used_by": ["ghost_tool"]}],
    })
    fs = probe_secrets_scoping(spec)
    assert any(f.severity == "LOW" and "unused" in f.title.lower() for f in fs)


# ---- annotation_compliance ------------------------------------------------
def test_missing_annotations_medium():
    spec = MCPServerSpec.from_dict({
        "name": "n", "tools": [{"name": "search", "description": "search"}]
    })
    fs = probe_annotation_compliance(spec)
    assert any(f.severity == "MEDIUM" and "no MCP annotations" in f.title for f in fs)


def test_readonly_name_mismatch_high():
    fs = probe_annotation_compliance(bad_spec())
    assert any(f.severity == "HIGH" and "mismatch" in f.title for f in fs)


# ---- prompt_injection -----------------------------------------------------
def test_trusted_prompt_with_input_medium():
    fs = probe_prompt_injection(bad_spec())
    assert any(f.severity == "MEDIUM" and "Trusted prompt" in f.title for f in fs)


def test_injection_directive_low():
    fs = probe_prompt_injection(bad_spec())
    assert any(f.severity == "LOW" and "directive language" in f.title for f in fs)


# ---- transport_security ---------------------------------------------------
def test_http_no_tls_high():
    fs = probe_transport_security(bad_spec())
    assert any(f.severity == "HIGH" and "Unencrypted transport" in f.title for f in fs)


def test_http_no_auth_medium():
    fs = probe_transport_security(bad_spec())
    assert any(f.severity == "MEDIUM" and "No auth" in f.title for f in fs)


def test_stdio_info():
    fs = probe_transport_security(good_spec())
    assert any(f.severity == "INFO" and "stdio" in f.title for f in fs)


# ---- least_privilege ------------------------------------------------------
def test_capabilities_without_tools_low():
    spec = MCPServerSpec.from_dict({
        "name": "n", "secrets": [{"name": "K", "source": "env:K"}]
    })
    fs = probe_least_privilege(spec)
    assert any(f.severity == "LOW" and "without any tools" in f.title for f in fs)


# ---- run_probes end-to-end ------------------------------------------------
def test_run_probes_good_only_info():
    fs = run_probes(good_spec())
    assert all(f.severity == "INFO" for f in fs)


def test_run_probes_bad_has_critical():
    fs = run_probes(bad_spec())
    assert any(f.severity == "CRITICAL" for f in fs)
