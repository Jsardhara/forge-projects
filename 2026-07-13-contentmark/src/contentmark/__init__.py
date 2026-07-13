"""contentmark — transparent AI-content signal detector + provenance toolkit."""
from __future__ import annotations

from .badge import (
    badge_css,
    badge_html,
    badge_script,
    band_label,
)
from .detector import detect
from .models import (
    DetectionReport,
    LikelihoodBand,
    Provenance,
    ProvenanceLabel,
    SignalId,
    SignatureVerification,
)
from .watermark import embed, verify

__all__ = [
    "detect",
    "embed",
    "verify",
    "badge_html",
    "badge_css",
    "badge_script",
    "band_label",
    "DetectionReport",
    "LikelihoodBand",
    "Provenance",
    "ProvenanceLabel",
    "SignalId",
    "SignatureVerification",
]
