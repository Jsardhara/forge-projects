"""Data models for mcpshield — MCP server security analyzer.

All models are frozen dataclasses for immutability. Severity is a string enum
("CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "INFO").
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


# --------------------------------------------------------------------------
# Input specification models (what an MCP server declares about itself)
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str = ""
    # MCP tool annotations: readOnlyHint, destructiveHint, idempotentHint, openWorldHint
    annotations: Optional[dict] = None
    input_schema: dict = field(default_factory=dict)


@dataclass(frozen=True)
class EgressRule:
    dest: str  # host, URL, or wildcard token
    scope: str = "specific"  # "specific" | "wildcard"


@dataclass(frozen=True)
class SecretRef:
    name: str
    source: str = "env"  # "env:FOO" | "hardcoded" | "file:/path" | "vault:..."
    scoped: bool = True  # tied to a specific tool/use vs one global token
    used_by: tuple = field(default_factory=tuple)  # tool names that reference it


@dataclass(frozen=True)
class PromptSpec:
    name: str
    template: str = ""
    trusted: bool = False  # if True, agent treats output as trusted instruction


@dataclass(frozen=True)
class ResourceSpec:
    name: str
    uri: str = ""
    writable: bool = False


@dataclass(frozen=True)
class MCPServerSpec:
    name: str
    transport: str = "stdio"  # stdio | http | sse
    auth: bool = False
    tls: bool = False
    tools: tuple = field(default_factory=tuple)
    egress: tuple = field(default_factory=tuple)
    secrets: tuple = field(default_factory=tuple)
    prompts: tuple = field(default_factory=tuple)
    resources: tuple = field(default_factory=tuple)

    @classmethod
    def from_dict(cls, d: dict) -> "MCPServerSpec":
        from mcpshield.loader import spec_from_dict

        return spec_from_dict(d)


# --------------------------------------------------------------------------
# Output models (analysis results)
# --------------------------------------------------------------------------
SEVERITIES = ("CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO")
SEVERITY_WEIGHT = {"CRITICAL": 25, "HIGH": 12, "MEDIUM": 5, "LOW": 2, "INFO": 0}


@dataclass(frozen=True)
class Finding:
    probe: str
    severity: str
    title: str
    detail: str
    recommendation: str = ""

    def to_dict(self) -> dict:
        return {
            "probe": self.probe,
            "severity": self.severity,
            "title": self.title,
            "detail": self.detail,
            "recommendation": self.recommendation,
        }


@dataclass(frozen=True)
class Report:
    server: str
    findings: tuple = field(default_factory=tuple)
    risk_score: int = 0
    band: str = "PASS"  # PASS | WARN | FAIL
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def failed(self) -> bool:
        return self.band == "FAIL"

    @property
    def passed(self) -> bool:
        return self.band != "FAIL"

    def to_dict(self) -> dict:
        d = {
            "server": self.server,
            "risk_score": self.risk_score,
            "band": self.band,
            "generated_at": self.generated_at.isoformat(),
            "findings": [f.to_dict() for f in self.findings],
        }
        return d
