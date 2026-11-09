"""The decision: does this workload fit in this host's RAM *right now*.

One rule carries most of the weight: **swap is never counted as capacity.**
A workload that only fits once the kernel starts paging is not fitting, it is
thrashing — so swap is reported and never added to the available budget.
"""

from dataclasses import dataclass, field

GIB = 1024 ** 3

FIT = "FIT"
TIGHT = "TIGHT"
BLOCKED_NOW = "BLOCKED_NOW"
IMPOSSIBLE = "IMPOSSIBLE"
UNMEASURED = "UNMEASURED"

EXIT_CODES = {FIT: 0, TIGHT: 1, BLOCKED_NOW: 1, IMPOSSIBLE: 1, UNMEASURED: 2}


@dataclass(frozen=True)
class Requirement:
    name: str
    peak_bytes: int
    shm_bytes: int = 0
    headroom_pct: float = 10.0


@dataclass(frozen=True)
class Verdict:
    state: str
    reasons: list = field(default_factory=list)
    reclaim_needed: int = 0
    requirement: Requirement = None
    margin: int = None

    @property
    def exit_code(self):
        return EXIT_CODES[self.state]


def _gib(value):
    if value is None:
        return "unknown"
    return "%.1f" % (value / GIB)


def evaluate(snapshot, requirement, shm_available=None):
    req = requirement
    if not snapshot.measured:
        return Verdict(
            state=UNMEASURED,
            reasons=["memory not measured: %s" % snapshot.unmeasured_reason],
            requirement=req,
        )

    reasons = [
        "%s GiB available of %s GiB total" % (_gib(snapshot.available), _gib(snapshot.total)),
        "%s GiB required" % _gib(req.peak_bytes),
    ]
    if snapshot.swap_free:
        reasons.append(
            "%s GiB swap free, not counted as capacity" % _gib(snapshot.swap_free)
        )

    if req.peak_bytes > snapshot.total:
        reasons.append("peak exceeds physical total: cannot fit even with everything else stopped")
        return Verdict(state=IMPOSSIBLE, reasons=reasons, requirement=req)

    if req.shm_bytes and shm_available is not None and shm_available < req.shm_bytes:
        reasons.append(
            "/dev/shm short: %s GiB available, %s GiB required"
            % (_gib(shm_available), _gib(req.shm_bytes))
        )
        return Verdict(state=BLOCKED_NOW, reasons=reasons, requirement=req)

    margin = snapshot.available - req.peak_bytes
    headroom = int(req.peak_bytes * req.headroom_pct / 100.0)

    if margin >= headroom:
        reasons.append("margin %s GiB >= %s GiB headroom" % (_gib(margin), _gib(headroom)))
        return Verdict(state=FIT, reasons=reasons, requirement=req, margin=margin)

    if margin >= 0:
        reasons.append(
            "margin %s GiB < %s GiB headroom: works, but with no room for another process"
            % (_gib(margin), _gib(headroom))
        )
        return Verdict(state=TIGHT, reasons=reasons, requirement=req, margin=margin)

    reasons.append(
        "short by %s GiB: something must be stopped first" % _gib(-margin)
    )
    return Verdict(
        state=BLOCKED_NOW,
        reasons=reasons,
        reclaim_needed=-margin,
        requirement=req,
        margin=margin,
    )
