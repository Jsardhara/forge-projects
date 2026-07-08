"""apk-signal — static triage signal extractor for Android APKs.

Treats an APK as a ZIP and scans raw entry bytes for network indicators,
hardcoded secrets, declared permissions, and suspicious capability keywords.
Zero external dependencies.
"""

from .analyzer import analyze
from .models import AnalysisResult, Severity, Signal, SignalType

__all__ = ["analyze", "AnalysisResult", "Severity", "Signal", "SignalType"]
__version__ = "0.1.0"
