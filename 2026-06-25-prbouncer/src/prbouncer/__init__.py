"""PRBouncer — PR spam detection engine for open source maintainers."""

from prbouncer.models import PullRequest, AuthorProfile, SpamSignal, SignalType, Verdict
from prbouncer.engine import SpamEngine

__all__ = ["PullRequest", "AuthorProfile", "SpamSignal", "SignalType", "Verdict", "SpamEngine"]
__version__ = "0.1.0"
