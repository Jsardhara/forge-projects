"""Loader: build an MCPServerSpec from a plain dict (parsed JSON/YAML)."""
from __future__ import annotations

from dataclasses import field
from typing import Any

from mcpshield.models import (
    EgressRule,
    MCPServerSpec,
    PromptSpec,
    ResourceSpec,
    SecretRef,
    ToolSpec,
)


def _as_tuple(v: Any) -> tuple:
    if v is None:
        return ()
    if isinstance(v, (list, tuple)):
        return tuple(v)
    return (v,)


def _opt_dict(v: Any) -> dict | None:
    if v is None or v == {}:
        return None
    return v if isinstance(v, dict) else {"raw": str(v)}


def spec_from_dict(d: dict) -> MCPServerSpec:
    if not isinstance(d, dict):
        raise TypeError("spec must be a dict")

    tools = tuple(
        ToolSpec(
            name=t.get("name", ""),
            description=t.get("description", ""),
            annotations=_opt_dict(t.get("annotations")),
            input_schema=t.get("input_schema") or {},
        )
        for t in _as_tuple(d.get("tools"))
    )

    egress = tuple(
        EgressRule(
            dest=e.get("dest", ""),
            scope=e.get("scope", "wildcard" if _is_wildcard(e.get("dest", "")) else "specific"),
        )
        for e in _as_tuple(d.get("egress"))
    )

    secrets = tuple(
        SecretRef(
            name=s.get("name", ""),
            source=s.get("source", "env"),
            scoped=bool(s.get("scoped", True)),
            used_by=tuple(_as_tuple(s.get("used_by"))),
        )
        for s in _as_tuple(d.get("secrets"))
    )

    prompts = tuple(
        PromptSpec(
            name=p.get("name", ""),
            template=p.get("template", ""),
            trusted=bool(p.get("trusted", False)),
        )
        for p in _as_tuple(d.get("prompts"))
    )

    resources = tuple(
        ResourceSpec(
            name=r.get("name", ""),
            uri=r.get("uri", ""),
            writable=bool(r.get("writable", False)),
        )
        for r in _as_tuple(d.get("resources"))
    )

    return MCPServerSpec(
        name=d.get("name", "unnamed-server"),
        transport=d.get("transport", "stdio"),
        auth=bool(d.get("auth", False)),
        tls=bool(d.get("tls", False)),
        tools=tools,
        egress=egress,
        secrets=secrets,
        prompts=prompts,
        resources=resources,
    )


def _is_wildcard(dest: str) -> bool:
    d = (dest or "").strip().lower()
    return d in {"*", "any", "0.0.0.0", "0.0.0.0/0", "::", "internet", "all"}
