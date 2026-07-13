"""Transparent heuristic signals for AI-content detection (contentmark).

All signals are deterministic, dependency-free, and fully explainable.
They measure *writing-style* tells commonly associated with machine-generated
prose — they do NOT constitute proof. See README for scope/limitations.
"""
from __future__ import annotations

import re
from math import log

_ws_split = re.compile(r"\s+")
_terminal = re.compile(r"(?<=[.!?])\s+")
_word_re = re.compile(r"[A-Za-z0-9']+")
_digit_re = re.compile(r"\d")


def _sentences(text: str) -> list[str]:
    parts = _terminal.split(text.strip())
    return [p for p in parts if p.strip()]


def _words(text: str) -> list[str]:
    return _word_re.findall(text)


def _clamp01(x: float) -> float:
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def _std(values: list[float]) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    mean = sum(values) / n
    return (sum((v - mean) ** 2 for v in values) / n) ** 0.5


# Lexical "tells" associated with fluent-but-flat machine prose.
_CONNECTORS = {
    "moreover", "furthermore", "additionally", "consequently", "therefore",
    "thus", "hence", "nonetheless", "nevertheless", "whereas", "notably",
    "importantly", "overall", "in summary", "to summarize", "in conclusion",
    "it is important to", "delve", "navigate", "leverage", "underscore",
    "in the realm of", "in today's", "it is worth",
}
_LOW_PERPLEXITY = {
    "the", "and", "to", "of", "in", "is", "that", "this", "it", "for",
    "as", "with", "on", "are", "be", "can", "will", "would", "could",
    "may", "should", "important", "various", "numerous", "significant",
    "essential", "crucial", "key", "role", "context", "realm",
}
_FILLERS = {
    "essentially", "basically", "simply", "certainly", "arguably", "indeed",
    "overall", "ultimately", "specifically", "particularly", "generally",
    "typically", "notably", "clearly",
}


def burstiness_signal(text: str) -> tuple[float, str]:
    """Low variation in sentence length = machine-like flatness."""
    sents = _sentences(text)
    lens = [len(_words(s)) for s in sents if _words(s)]
    if len(lens) < 3:
        return 0.0, "too few sentences to assess burstiness"
    mean = sum(lens) / len(lens)
    cv = (_std(lens) / mean) if mean else 0.0
    raw = _clamp01((0.40 - cv) / 0.45)
    return raw, f"CV of sentence length = {cv:.3f} (mean {mean:.1f} words)"


def repetition_signal(text: str) -> tuple[float, str]:
    """Low type-token ratio = repeated vocabulary (common in generated text)."""
    words = [w.lower() for w in _words(text)]
    if len(words) < 25:
        return 0.0, "too few words to assess repetition"
    ttr = len(set(words)) / len(words)
    raw = _clamp01((0.72 - ttr) / 0.28)
    return raw, f"type-token ratio = {ttr:.3f}"


def connector_frequency_signal(text: str) -> tuple[float, str]:
    low = text.lower()
    words = [w.lower() for w in _words(text)]
    if not words:
        return 0.0, "no words"
    count = 0
    for c in _CONNECTORS:
        count += low.count(c)
    freq = count / len(words) * 100.0
    raw = _clamp01((freq - 4.0) / 5.0)
    return raw, f"{freq:.2f} connector phrases per 100 words"


def low_perplexity_signal(text: str) -> tuple[float, str]:
    words = [w.lower() for w in _words(text)]
    if not words:
        return 0.0, "no words"
    common = sum(1 for w in words if w in _LOW_PERPLEXITY)
    ratio = common / len(words)
    raw = _clamp01((ratio - 0.10) / 0.12)
    return raw, f"{ratio:.3f} common-word ratio"


def filler_density_signal(text: str) -> tuple[float, str]:
    words = [w.lower() for w in _words(text)]
    if not words:
        return 0.0, "no words"
    fillers = sum(1 for w in words if w in _FILLERS)
    ratio = fillers / len(words)
    raw = _clamp01((ratio - 0.02) / 0.05)
    return raw, f"{ratio:.3f} filler-word ratio"


def enumeration_signal(text: str) -> tuple[float, str]:
    """Numbered/bulleted enumeration patterns common in structured output."""
    count = 0
    count += len(re.findall(r"(?m)^\s*(?:\d+[.)]|[-*•])\s+", text))
    count += len(re.findall(r"\b(first|second|third|fourth|fifth|finally)\b", text.lower()))
    count += len(re.findall(r"\b(on the one hand|on the other hand)\b", text.lower()))
    raw = _clamp01(count / 3.0)
    return raw, f"{count} enumeration markers"


def sentence_uniformity_signal(text: str) -> tuple[float, str]:
    """Uniform sentence length (low CV) -> machine cadence."""
    sents = _sentences(text)
    lens = [len(_words(s)) for s in sents if _words(s)]
    if len(lens) < 3:
        return 0.0, "too few sentences to assess uniformity"
    mean = sum(lens) / len(lens)
    cv = (_std(lens) / mean) if mean else 0.0
    raw = _clamp01((0.40 - cv) / 0.45)
    return raw, f"length CV = {cv:.3f}"
