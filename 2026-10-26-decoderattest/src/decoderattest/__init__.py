"""decoderattest - which Brotli decoder is actually loaded on this host?

Standard library only. The public surface is deliberately small: load a rule file,
inventory the local runtimes, attest, render.
"""

from __future__ import annotations

__version__ = "1.0.0"

from .attest import Attestation, Finding, attest, severity_for
from .report import render_json, render_text, to_dict
from .rules import RuleError, RuleSet, default_rules_path

__all__ = [
    "__version__",
    "Attestation",
    "Finding",
    "attest",
    "severity_for",
    "render_json",
    "render_text",
    "to_dict",
    "RuleError",
    "RuleSet",
    "default_rules_path",
]
