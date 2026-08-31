"""capalarm — subscription AI plan-cap compliance & headroom forecaster.

Given a user's actual usage records (CSV or JSON) and the token/rate caps of their
capped AI subscription plans, capalarm reports:
  - how much of the hard token cap has been consumed (headroom %)
  - soft-cap / hard-cap breach alerts
  - peak tokens/minute vs the plan's rate-limit tier
  - a linear days-to-breach forecast so teams get proactive warning.
"""

from capalarm.version import __version__

__all__ = ["__version__"]