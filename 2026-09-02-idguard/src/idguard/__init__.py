"""idguard — identity-exposure & breach-notification compliance screener."""

from idguard.engine import aggregate, exit_code, scan_record, RecordResult, ScanTotals
from idguard.notify import build_notification_plan

__version__ = "0.1.0"
__all__ = [
    "aggregate",
    "build_notification_plan",
    "exit_code",
    "scan_record",
    "RecordResult",
    "ScanTotals",
    "__version__",
]