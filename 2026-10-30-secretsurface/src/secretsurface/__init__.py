"""secretsurface -- where key material actually lives, by class.

Read-only. Offline. Never emits a credential value.
"""

__version__ = "1.0.0"

from .patterns import PATTERNS, Match, fingerprint, find_matches, is_placeholder
from .classify import CLASSES, classify_path
from .scan import scan
from .report import Finding, Report

__all__ = [
    "PATTERNS", "Match", "find_matches", "is_placeholder", "fingerprint",
    "CLASSES", "classify_path", "scan", "Finding", "Report", "__version__",
]
