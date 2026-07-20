"""Shared test fixtures for aidisclose tests.

NOTE: imported as ``from fixtures import ...`` (bare) -- NOT ``from tests.fixtures``.
The project lives inside a directory that is itself under a pytest rootdir
(jarvis), which leaks a top-level ``tests`` package; the bare form is the
documented workaround.
"""
from datetime import date

from aidisclose.models import OrgProfile

DEFAULT_REF = date(2026, 7, 20)


def make_profile(name="TestCo", sectors=(), jurisdictions=(),
                 ai_uses=(), implemented=(), reference_date=None):
    return OrgProfile(
        name=name,
        sectors=tuple(sectors),
        jurisdictions=tuple(jurisdictions),
        ai_uses=tuple(ai_uses),
        implemented=tuple(implemented),
        reference_date=reference_date or DEFAULT_REF,
    )
