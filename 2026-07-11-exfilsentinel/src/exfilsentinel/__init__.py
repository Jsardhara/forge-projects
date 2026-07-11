"""exfilsentinel — AI model-access exfiltration detection + output provenance."""

from .detector import DetectionEngine
from .models import (
    ApiEvent,
    ExtractionSignal,
    ExtractionVerdict,
    ProvenanceRecord,
    RiskClass,
    Watermark,
)
from .watermark import detect, embed, verify

__all__ = [
    "DetectionEngine",
    "ApiEvent",
    "ExtractionSignal",
    "ExtractionVerdict",
    "ProvenanceRecord",
    "RiskClass",
    "Watermark",
    "detect",
    "embed",
    "verify",
]
