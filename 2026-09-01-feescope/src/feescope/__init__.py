"""feescope -- ad-spend surcharge & fee-opaqueness audit scanner."""

from .engine import FeeScopeScanner, ScanConfig
from .models import FeeItem, Finding, InvoiceReport, Severity, Verdict

__all__ = [
    "FeeScopeScanner",
    "ScanConfig",
    "FeeItem",
    "Finding",
    "InvoiceReport",
    "Severity",
    "Verdict",
]

__version__ = "0.1.0"