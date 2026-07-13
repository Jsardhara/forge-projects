"""Tests for the detection orchestrator."""
from contentmark import detect
from contentmark.models import LikelihoodBand

from fixtures import HUMAN_TEXT, AI_TEXT, SHORT_TEXT


def test_detect_human_reads_human():
    rep = detect(HUMAN_TEXT)
    assert rep.band == LikelihoodBand.HUMAN
    assert rep.normalized_score < 0.45


def test_detect_ai_reads_ai():
    rep = detect(AI_TEXT)
    assert rep.band in (LikelihoodBand.LIKELY_AI, LikelihoodBand.VERY_LIKELY_AI)
    assert rep.normalized_score > 0.45


def test_detect_ai_scores_higher_than_human():
    ai = detect(AI_TEXT)
    human = detect(HUMAN_TEXT)
    assert ai.normalized_score > human.normalized_score


def test_short_text_never_accused():
    rep = detect(SHORT_TEXT)
    assert rep.band == LikelihoodBand.HUMAN
    assert rep.word_count < 40


def test_all_seven_signals_present():
    rep = detect(AI_TEXT)
    ids = {s.signal_id.value for s in rep.scores}
    assert len(ids) == 7


def test_contributions_sum_to_raw():
    rep = detect(AI_TEXT)
    total = sum(s.contribution for s in rep.scores)
    assert abs(total - rep.overall_raw) < 1e-9


def test_normalized_in_zero_one():
    rep = detect(AI_TEXT)
    assert 0.0 <= rep.normalized_score <= 1.0


def test_explain_includes_band():
    rep = detect(AI_TEXT)
    out = rep.explain()
    assert rep.band.value in out


def test_full_coverage_all_signals_positive_on_ai():
    rep = detect(AI_TEXT)
    assert all(s.raw_score >= 0.0 for s in rep.scores)
    # At least the strong tell signals should fire on the AI sample.
    fired = [s for s in rep.scores if s.raw_score > 0.2]
    assert len(fired) >= 4


def test_empty_text_safe():
    rep = detect("")
    assert rep.band == LikelihoodBand.HUMAN
    assert rep.word_count == 0


def test_report_to_dict_roundtrips():
    rep = detect(AI_TEXT)
    d = rep.to_dict()
    assert d["band"] == rep.band.value
    assert len(d["signals"]) == 7
