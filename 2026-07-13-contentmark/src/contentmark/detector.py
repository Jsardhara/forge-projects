"""Detection orchestrator for contentmark."""
from __future__ import annotations

from .models import (
    DetectionReport,
    LikelihoodBand,
    SignalId,
    SignalResult,
    band_for_score,
    clamp01,
)
from .signals import (
    burstiness_signal,
    connector_frequency_signal,
    enumeration_signal,
    filler_density_signal,
    low_perplexity_signal,
    repetition_signal,
    sentence_uniformity_signal,
)
from .signals import _sentences, _words

_WEIGHTS = {
    # Strong, separating tells — weighted heavily.
    SignalId.BURSTINESS: 0.30,
    SignalId.CONNECTOR_FREQUENCY: 0.30,
    SignalId.ENUMERATION_DENSITY: 0.20,
    SignalId.SENTENCE_UNIFORMITY: 0.20,
    # Informational-only signals (poor discriminators on fluent text; reported,
    # not scored, so they never inflate or deflate the band).
    SignalId.REPETITION: 0.0,
    SignalId.LOW_PERPLEXITY_WORDS: 0.0,
    SignalId.FILLER_DENSITY: 0.0,
}

_RUNNERS = {
    SignalId.BURSTINESS: burstiness_signal,
    SignalId.REPETITION: repetition_signal,
    SignalId.CONNECTOR_FREQUENCY: connector_frequency_signal,
    SignalId.LOW_PERPLEXITY_WORDS: low_perplexity_signal,
    SignalId.FILLER_DENSITY: filler_density_signal,
    SignalId.ENUMERATION_DENSITY: enumeration_signal,
    SignalId.SENTENCE_UNIFORMITY: sentence_uniformity_signal,
}

# Deterministic normalization denominator = sum of weights (all raw in 0..1).
_NORM = sum(_WEIGHTS.values())

_MIN_WORDS = 40


def detect(text: str) -> DetectionReport:
    words = _words(text)
    sentences = _sentences(text)
    results: list[SignalResult] = []
    raw_total = 0.0
    for sid, runner in _RUNNERS.items():
        raw_score, detail = runner(text)
        raw_score = clamp01(raw_score)
        w = _WEIGHTS[sid]
        contribution = w * raw_score
        raw_total += contribution
        results.append(
            SignalResult(
                signal_id=sid,
                weight=w,
                raw_score=raw_score,
                contribution=contribution,
                detail=detail,
            )
        )
    normalized = clamp01(raw_total / _NORM)
    band = band_for_score(normalized)

    # Insufficient text => never accuse. Downgrade the band for short inputs.
    if len(words) < _MIN_WORDS:
        band = LikelihoodBand.HUMAN
        normalized = min(normalized, 0.25)

    return DetectionReport(
        char_count=len(text),
        word_count=len(words),
        sentence_count=len(sentences),
        scores=results,
        overall_raw=raw_total,
        normalized_score=normalized,
        band=band,
    )
