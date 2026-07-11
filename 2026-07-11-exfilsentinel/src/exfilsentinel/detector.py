from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional, Sequence

from .models import ApiEvent, ExtractionSignal, ExtractionVerdict, RiskClass

# --- Signal weights (sum of triggered weights normalizes the final risk) ---
WEIGHTS: dict[str, float] = {
    "volume_burst": 0.25,
    "repetitive_prompt": 0.20,
    "completion_heavy": 0.15,
    "rate_spike": 0.15,
    "sensitive_model_access": 0.20,
    "download_pattern": 0.30,
    "off_hours": 0.08,
    "offboarding_window": 0.20,
}

# --- Thresholds ---
VOLUME_FULL = 1_000_000  # completion tokens at/above which volume_burst raw = 1.0
HUMAN_PACE_RPS = 0.05  # at/below this request rate there is no rate concern
RATE_FULL_RPS = 5.0  # at/above this request rate raw = 1.0
SENSITIVE_MARKERS = ("ft:", "internal", "private", "proprietary")
DOWNLOAD_MARKERS = ("download", "export", "dataset", "weights", "/files", "bulk")
OFFBOARDING_GRACE = timedelta(days=30)
NOISE_FLOOR = 1e-3  # signals below 0.1% contribution are not 'triggered'

# --- Classification thresholds ---
BENIGN_MAX = 0.25
SUSPICIOUS_MAX = 0.65
OFFBOARDING_BOOST = 1.25
ALLOWLIST_CREDIT = 0.30


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def _volume_burst(events: list[ApiEvent]) -> float:
    total = sum(e.completion_tokens for e in events)
    return _clamp(total / VOLUME_FULL)


def _repetitive_prompt(events: list[ApiEvent]) -> float:
    if len(events) < 2:
        return 0.0
    templates = [
        e.prompt_template_hash or f"{e.prompt_tokens}:{e.model}" for e in events
    ]
    diversity = len(set(templates)) / len(events)
    return _clamp(1.0 - diversity)


def _completion_heavy(events: list[ApiEvent]) -> float:
    pt = sum(e.prompt_tokens for e in events)
    ct = sum(e.completion_tokens for e in events)
    total = pt + ct
    if total == 0:
        return 0.0
    ratio = ct / total
    return _clamp((ratio - 0.5) / 0.5)


def _rate_spike(events: list[ApiEvent]) -> float:
    if len(events) < 2:
        return 0.0
    times = sorted(e.timestamp for e in events)
    span = max((times[-1] - times[0]).total_seconds(), 1.0)
    rps = len(events) / span
    if rps <= HUMAN_PACE_RPS:
        return 0.0
    return _clamp(rps / RATE_FULL_RPS)


def _sensitive_model_access(events: list[ApiEvent]) -> float:
    for e in events:
        low = e.model.lower()
        if any(m in low for m in SENSITIVE_MARKERS):
            return 0.5
    return 0.0


def _download_pattern(events: list[ApiEvent]) -> float:
    for e in events:
        low = e.endpoint.lower()
        if any(m in low for m in DOWNLOAD_MARKERS):
            return 0.5
    return 0.0


def _off_hours(events: list[ApiEvent]) -> float:
    if not events:
        return 0.0
    night = sum(1 for e in events if 0 <= e.timestamp.hour < 6)
    return _clamp(night / len(events))


def _offboarding_window(
    events: list[ApiEvent], offboarding_since: Optional[datetime]
) -> float:
    if offboarding_since is None:
        return 0.0
    if offboarding_since.tzinfo is None:
        offboarding_since = offboarding_since.replace(tzinfo=timezone.utc)
    window_start = offboarding_since - OFFBOARDING_GRACE
    for e in events:
        ts = e.timestamp
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        if window_start <= ts <= offboarding_since:
            return 1.0
    return 0.0


class DetectionEngine:
    """Scores an actor's model-API access for exfiltration behavior."""

    def __init__(self, weights: Optional[dict[str, float]] = None) -> None:
        self.weights = dict(WEIGHTS)
        if weights:
            self.weights.update(weights)

    def evaluate(
        self,
        actor_id: str,
        events: Sequence[ApiEvent],
        offboarding_since: Optional[datetime] = None,
        allowlisted: bool = False,
    ) -> ExtractionVerdict:
        actor_events = [e for e in events if e.actor_id == actor_id]
        signals: list[ExtractionSignal] = []

        def add(name: str, raw: float, detail: str = "") -> None:
            signals.append(
                ExtractionSignal(
                    name=name, weight=self.weights.get(name, 0.0), raw_score=raw, detail=detail
                )
            )

        add("volume_burst", _volume_burst(actor_events))
        add("repetitive_prompt", _repetitive_prompt(actor_events))
        add("completion_heavy", _completion_heavy(actor_events))
        add("rate_spike", _rate_spike(actor_events))
        add("sensitive_model_access", _sensitive_model_access(actor_events))
        add("download_pattern", _download_pattern(actor_events))
        add("off_hours", _off_hours(actor_events))
        ob = _offboarding_window(actor_events, offboarding_since)
        add("offboarding_window", ob)

        triggered = [s for s in signals if s.raw_score > NOISE_FLOOR]
        if not triggered:
            risk = 0.0
        else:
            num = sum(s.weight * s.raw_score for s in triggered)
            den = sum(s.weight for s in triggered)
            risk = num / den if den else 0.0

        boosted = ob > 0.0
        if boosted:
            risk = _clamp(risk * OFFBOARDING_BOOST)
        if allowlisted:
            risk = _clamp(risk - ALLOWLIST_CREDIT)

        return ExtractionVerdict(
            actor_id=actor_id,
            risk_score=round(risk, 4),
            risk_class=self._classify(risk),
            signals=tuple(signals),
            evidence=tuple(self._evidence(actor_events, triggered, boosted, allowlisted)),
        )

    @staticmethod
    def _classify(risk: float) -> RiskClass:
        if risk > SUSPICIOUS_MAX:
            return RiskClass.EXFILTRATION
        if risk > BENIGN_MAX:
            return RiskClass.SUSPICIOUS
        return RiskClass.BENIGN

    @staticmethod
    def _evidence(events, triggered, boosted, allowlisted):
        ev: list[str] = []
        if triggered:
            ev.append(
                f"{len(triggered)} exfiltration signal(s) triggered across {len(events)} events"
            )
        for s in triggered:
            ev.append(f"  - {s.name}: raw={s.raw_score:.2f} weight={s.weight}")
        if boosted:
            ev.append("offboarding window active: risk boosted x1.25")
        if allowlisted:
            ev.append("actor allowlisted: risk reduced by 0.30")
        return ev
