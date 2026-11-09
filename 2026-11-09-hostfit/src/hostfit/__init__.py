"""hostfit — will this workload fit in this host's RAM right now?"""

from .verdict import (  # noqa: F401
    BLOCKED_NOW,
    FIT,
    IMPOSSIBLE,
    TIGHT,
    UNMEASURED,
    Requirement,
    Verdict,
    evaluate,
)

__version__ = "1.0.0"
