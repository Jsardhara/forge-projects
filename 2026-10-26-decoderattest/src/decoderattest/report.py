"""Rendering: one human table, one machine document, same facts.

The witness rule for this module: whatever the JSON says, the text says. If a
field is missing from one renderer it is missing from the artifact someone will
paste into a ticket, so both are generated from the same dataclasses.
"""

from __future__ import annotations

import json
from typing import Dict

from .attest import Attestation

__all__ = ["to_dict", "render_text", "render_json"]

_RULE = "-" * 78


def to_dict(attestation: Attestation) -> Dict:
    return {
        "advisory": dict(attestation.advisory),
        "verdict": attestation.verdict,
        "counts": dict(attestation.counts),
        "notes": list(attestation.notes),
        "findings": [finding.to_dict() for finding in attestation.findings],
    }


def render_json(attestation: Attestation) -> str:
    return json.dumps(to_dict(attestation), indent=2, sort_keys=True, ensure_ascii=True)


def render_text(attestation: Attestation) -> str:
    advisory = attestation.advisory or {}
    lines = [
        "decoderattest - %s (%s)" % (
            advisory.get("id", "unknown advisory"),
            " / ".join(advisory.get("aliases", [])[:2]) or "no aliases",
        ),
        advisory.get("summary", ""),
        advisory.get("url", ""),
        _RULE,
        "VERDICT: %s" % attestation.verdict,
        _RULE,
    ]

    if not attestation.findings:
        lines.append("no targets attested")
    for finding in attestation.findings:
        lines.append(_finding_block(finding))

    counts = attestation.counts
    lines.append(_RULE)
    lines.append(
        "counts: found %(found)d | affected %(affected)d | patched %(patched)d "
        "| unknown %(unknown)d" % counts
    )
    for note in attestation.notes:
        lines.append("note: %s" % note)
    lines.append(
        "scope: local runtime inventory only - this is not a CVE scanner and makes no "
        "network calls"
    )
    return "\n".join(line for line in lines if line is not None)


def _finding_block(finding) -> str:
    header = "%-8s %-9s %-40s %-14s %s" % (
        finding.severity,
        finding.ecosystem,
        _shorten(finding.target, 40),
        finding.version or "unknown",
        finding.status,
    )
    detail = "         %s" % finding.reason
    if finding.fix_hint:
        detail += "\n         fix: %s" % finding.fix_hint
    return header + "\n" + detail


def _shorten(text: str, width: int) -> str:
    if len(text) <= width:
        return text
    return "..." + text[-(width - 3):]
