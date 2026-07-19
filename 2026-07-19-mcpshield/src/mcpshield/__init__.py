"""mcpshield public API."""
from __future__ import annotations

from mcpshield.loader import spec_from_dict
from mcpshield.models import (
    EgressRule,
    Finding,
    MCPServerSpec,
    PromptSpec,
    Report,
    ResourceSpec,
    SecretRef,
    ToolSpec,
)
from mcpshield.probes import ALL_PROBES, run_probes
from mcpshield.scoring import score_findings

__version__ = "0.1.0"
__all__ = [
    "MCPServerSpec", "ToolSpec", "EgressRule", "SecretRef", "PromptSpec",
    "ResourceSpec", "Finding", "Report", "spec_from_dict", "run_probes",
    "ALL_PROBES", "score_findings", "analyze",
]


def analyze(spec: MCPServerSpec) -> Report:
    """Run all probes on a spec and return a scored Report."""
    findings = run_probes(spec)
    risk_score, band = score_findings(findings)
    return Report(
        server=spec.name,
        findings=tuple(findings),
        risk_score=risk_score,
        band=band,
    )
