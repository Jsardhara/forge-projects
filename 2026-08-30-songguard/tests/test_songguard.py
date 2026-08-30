"""Tests for songguard lyric infringement screener."""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

import pytest

from songguard.models import SEVERITY_RANK, Severity, Verdict
from songguard.normalize import is_significant, shingles, tokenize
from songguard.scanner import (
    MIN_PHRASE,
    SongguardError,
    load_catalog,
    screen_file,
    screen_text,
)
from songguard.screener import containment, jaccard, longest_common_run

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


def _txt(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _catalog(*names: str) -> dict:
    return {n: _txt(n) for n in names}


# ---------------------------------------------------------------- normalize

def test_tokenize_lowercase_strips_punctuation():
    assert tokenize("Oh, WOW! We're on FIRE!!") == ["oh", "wow", "we're", "on", "fire"]


def test_tokenize_collapses_whitespace_and_drops_digits_ok():
    assert tokenize("one\n\n two   three") == ["one", "two", "three"]


def test_tokenize_keeps_apostrophe_contractions():
    assert "don't" in tokenize("I don't care")


def test_is_significant_excludes_function_words():
    assert not is_significant("the")
    assert is_significant("engine")


def test_shingles_drop_function_word_only_windows():
    tokens = ["the", "and", "engine", "burns"]
    s = shingles(tokens, n=2, min_significant=1)
    # ("engine","burns") kept; ("the","and") and ("and","engine") each have one sig
    assert ("engine", "burns") in s
    # a pure function pair is dropped
    assert ("and", "the") not in shingles(["and", "the"], n=2)


def test_shingles_empty_on_short_input():
    assert shingles(["a", "b"], n=3) == set()


# ---------------------------------------------------------------- similarity

def test_longest_common_run_finds_contiguous_phrase():
    a = ["midnight", "engine", "burns", "the", "neon"]
    b = ["we", "chase", "midnight", "engine", "burns", "skylight"]
    run, phrase = longest_common_run(a, b)
    assert run == 3
    assert phrase == "midnight engine burns"


def test_longest_common_run_zero_on_disjoint():
    assert longest_common_run(["a", "b"], ["c", "d"]) == (0, "")


def test_longest_common_run_empty_inputs():
    assert longest_common_run([], ["a"]) == (0, "")
    assert longest_common_run(["a"], []) == (0, "")


def test_containment_is_fraction_of_input():
    assert containment(100, 25) == 0.25
    assert containment(0, 5) == 0.0


def test_jaccard_midpoint():
    # sets {a,b,c} and {b,c,d}: inter=2, union=4
    assert jaccard(2, 3, 3) == 0.5


# ---------------------------------------------------------------- verdicts

def test_verbatim_sampling_flags_infringe():
    report = screen_text(
        _txt("input_infringe.txt"),
        _catalog("reference_b_sampled.txt", "reference_a_garden.txt"),
    )
    assert report.verdict == Verdict.INFRINGE
    worst = max(report.matches, key=lambda m: SEVERITY_RANK[m.severity])
    assert worst.severity == Severity.FLAG
    assert worst.longest_run >= 16
    assert worst.sampled_phrase and "midnight engine" in worst.sampled_phrase
    assert report.score >= 60


def test_original_song_against_unrelated_catalog_is_clear():
    report = screen_text(
        _txt("input_original.txt"),
        _catalog("reference_b_sampled.txt", "reference_a_garden.txt"),
    )
    assert report.verdict == Verdict.CLEAR
    # incidental shared bigrams give tiny containment, but well under the flag gate
    assert report.score < 15
    assert all(m.severity == Severity.PASS for m in report.matches)
    assert all(m.longest_run < MIN_PHRASE for m in report.matches)


def test_short_common_phrase_coincidence_stays_clear():
    report = screen_text(
        _txt("input_coincidence.txt"),
        _catalog("reference_c_coincidence.txt"),
    )
    assert report.verdict == Verdict.CLEAR
    # the shared 5-token phrase must not trip the 6-token sampling gate
    assert all(m.longest_run < MIN_PHRASE for m in report.matches)


def test_paraphrase_cover_is_not_clear():
    # take reference_b's chorus and swap ~25% of content words for synonyms
    src = _txt("reference_b_sampled.txt")
    cover = src.replace("neon skylight", "bright skylight").replace(
        "every mile", "each mile"
    ).replace("we chase the river", "we follow the river").replace(
        "ash on the dashboard", "dust on the dashboard"
    )
    refs = _catalog("reference_b_sampled.txt")
    report_mem = screen_text(cover, refs)
    assert report_mem.verdict in (Verdict.REVIEW, Verdict.INFRINGE)


def test_cover_shortest_replacement_still_signals():
    # minimal paraphrasing should STILL hit the sampling gate
    src = _txt("reference_b_sampled.txt")
    cover = src.replace("neon skylight", "bright skylight")
    report = screen_text(cover, _catalog("reference_b_sampled.txt"))
    assert report.verdict in (Verdict.REVIEW, Verdict.INFRINGE)


def test_severity_dominant_across_references():
    # infringe input against a catalog that also has an unrelated ref
    refs = _catalog("reference_b_sampled.txt", "reference_a_garden.txt")
    report = screen_text(_txt("input_infringe.txt"), refs)
    worst = max(report.matches, key=lambda m: SEVERITY_RANK[m.severity])
    assert worst.severity == Severity.FLAG
    assert report.verdict == Verdict.INFRINGE


# ---------------------------------------------------------------- catalog

def test_load_catalog_directory_scans_text_files():
    refs = load_catalog(str(FIXTURES))
    assert "reference_b_sampled.txt" in refs
    assert "input_infringe.txt" in refs  # if present in same dir


def test_load_catalog_missing_raises():
    with pytest.raises(SongguardError):
        load_catalog(str(FIXTURES / "does_not_exist.txt"))


def test_screen_file_bad_reference_raises():
    with pytest.raises(SongguardError):
        screen_file(str(FIXTURES / "input_infringe.txt"),
                    str(FIXTURES / "nope_missing"))


def test_screen_file_sets_input_path_basename():
    report = screen_file(
        str(FIXTURES / "input_infringe.txt"),
        str(FIXTURES / "reference_b_sampled.txt"),
    )
    assert report.input_path == "input_infringe.txt"


# ---------------------------------------------------------------- CLI

def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "songguard", *args],
        capture_output=True,
        text=True,
        cwd=str(FIXTURES.parent.parent),
    )


def test_cli_screen_human_infringe():
    p = _run("screen", "tests/fixtures/input_infringe.txt",
             "tests/fixtures/reference_b_sampled.txt")
    assert p.returncode == 0
    assert "INFRINGE" in p.stdout
    assert "midnight engine" in p.stdout


def test_cli_screen_json_valid():
    p = _run("screen", "tests/fixtures/input_infringe.txt",
             "tests/fixtures/reference_b_sampled.txt", "--json")
    assert p.returncode == 0
    data = json.loads(p.stdout)
    assert data["verdict"] == "INFRINGE"
    assert data["flagged_references"] >= 1
    assert "sampled_phrase" in data["matches"][0]


def test_cli_check_clear_exit_zero():
    p = _run("check", "tests/fixtures/input_original.txt",
             "tests/fixtures/catalog_other")
    assert p.returncode == 0
    assert "PASS" in p.stdout or "CLEAR" in p.stdout


def test_cli_check_infringe_exit_one():
    p = _run("check", "tests/fixtures/input_infringe.txt",
             "tests/fixtures/catalog_other")
    assert p.returncode == 1


def test_cli_check_missing_input_exit_two():
    p = _run("check", "tests/fixtures/does_not_exist.txt",
             "tests/fixtures")
    assert p.returncode == 2


def test_cli_check_json_gate_field():
    p = _run("check", "tests/fixtures/input_infringe.txt",
             "tests/fixtures/reference_b_sampled.txt", "--json")
    data = json.loads(p.stdout)
    assert data["gate"] == "FAIL"


def test_cli_stdin_screen():
    src = _txt("input_infringe.txt")
    p = subprocess.run(
        [sys.executable, "-m", "songguard", "screen", "-",
         "tests/fixtures/reference_b_sampled.txt"],
        input=src, capture_output=True, text=True,
        cwd=str(FIXTURES.parent.parent),
    )
    assert p.returncode == 0
    assert "INFRINGE" in p.stdout