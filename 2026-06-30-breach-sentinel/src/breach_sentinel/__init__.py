"""BreachSentinel — open-source breach exposure monitoring.

Scans multiple breach sources (HaveIBeenPwned API, local breach dumps,
paste sites) for leaked credentials and identity documents, scores
exposure severity, and emits actionable alerts.

All-stdlib. Zero external dependencies.
"""

__version__ = "0.1.0"

from breach_sentinel.models import (
    Alert,
    BreachRecord,
    BreachSourceInfo,
    BreachType,
    ExposureScore,
    Identity,
    ScanResult,
    Severity,
)

__all__ = [
    "Alert",
    "BreachRecord",
    "BreachSourceInfo",
    "BreachType",
    "ExposureScore",
    "Identity",
    "ScanResult",
    "Severity",
    "__version__",
]
