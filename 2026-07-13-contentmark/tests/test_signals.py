"""Tests for signals module (individual heuristic correctness)."""
from contentmark.signals import (
    burstiness_signal,
    connector_frequency_signal,
    enumeration_signal,
    filler_density_signal,
    low_perplexity_signal,
    repetition_signal,
    sentence_uniformity_signal,
)
from contentmark.signals import _clamp01

from fixtures import HUMAN_TEXT, AI_TEXT, SHORT_TEXT


def test_burstiness_human_uniform_low():
    raw, _ = burstiness_signal(HUMAN_TEXT)
    # Human text has varied sentence lengths -> low AI signal.
    assert raw < 0.5


def test_burstiness_ai_high():
    raw, _ = burstiness_signal(AI_TEXT)
    assert raw > 0.5


def test_repetition_ai_at_least_human():
    raw_h, _ = repetition_signal(HUMAN_TEXT)
    raw_a, _ = repetition_signal(AI_TEXT)
    assert 0.0 <= raw_h <= 1.0
    assert 0.0 <= raw_a <= 1.0
    assert raw_a >= raw_h


def test_repetition_high_on_repetitive_text():
    # Synthetic low type-token-ratio text (>25 words) should score high.
    rep = ("the cat sat on the mat and the dog ran to the cat and the dog "
           "sat on the mat while the cat watched the dog and the mat held "
           "the cat and the dog and the cat and the dog and the mat and "
           "the cat and the dog and the cat and the dog and the mat again "
           "and the cat and the dog and the cat and the dog and the cat dog")
    raw, detail = repetition_signal(rep)
    assert raw > 0.5


def test_connector_frequency_ai_fires():
    raw, _ = connector_frequency_signal(AI_TEXT)
    assert raw > 0.5


def test_connector_frequency_human_low():
    raw, _ = connector_frequency_signal(HUMAN_TEXT)
    assert raw < 0.3


def test_low_perplexity_ai_high():
    raw, _ = low_perplexity_signal(AI_TEXT)
    assert raw > 0.2


def test_filler_density_ai_at_least_human():
    raw_h, _ = filler_density_signal(HUMAN_TEXT)
    raw_a, _ = filler_density_signal(AI_TEXT)
    assert 0.0 <= raw_h <= 1.0
    assert 0.0 <= raw_a <= 1.0
    assert raw_a >= raw_h


def test_filler_density_high_on_filler_text():
    rep = ("essentially the data is basically clear. " * 8)
    raw, _ = filler_density_signal(rep)
    assert raw > 0.3


def test_enumeration_ai_fires():
    raw, _ = enumeration_signal(AI_TEXT)
    assert raw > 0.5


def test_sentence_uniformity_ai_high():
    raw, _ = sentence_uniformity_signal(AI_TEXT)
    assert raw > 0.4


def test_short_text_signals_safe():
    raw, _ = burstiness_signal(SHORT_TEXT)
    assert raw == 0.0


def test_clamp01_bounds():
    assert _clamp01(-2.0) == 0.0
    assert _clamp01(2.0) == 1.0
    assert _clamp01(0.5) == 0.5
