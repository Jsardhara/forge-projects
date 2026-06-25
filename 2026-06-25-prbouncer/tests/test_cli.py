"""Tests for prbouncer.cli — command-line interface."""

import json
import subprocess
import sys

import pytest

from prbouncer.cli import main


class TestCliAnalyze:
    def test_legit_pr(self, capsys):
        main([
            "analyze",
            "--pr", "42",
            "--title", "Fix race condition in concurrent queue processor",
            "--body", "Resolves #42. The current implementation has a race condition.",
            "--author", "veteran",
            "--account-age", "730",
            "--followers", "50",
            "--linked-issues", "1",
        ])
        output = capsys.readouterr().out
        assert "PR #42" in output
        assert "LEGIT" in output

    def test_spam_pr(self, capsys):
        main([
            "analyze",
            "--pr", "99",
            "--title", "Update code",
            "--body", "I have analyzed the codebase and this PR improves the codebase.",
            "--author", "happy-84729",
            "--account-age", "0",
            "--linked-issues", "0",
            "--recent-prs", "12",
            "--files", "README.md",
        ])
        output = capsys.readouterr().out
        assert "PR #99" in output
        assert "SPAM" in output

    def test_json_output(self, capsys):
        main([
            "analyze",
            "--pr", "1",
            "--title", "Fix bug",
            "--body", "Normal fix",
            "--author", "dev",
            "--account-age", "365",
            "--linked-issues", "1",
            "--json",
        ])
        output = capsys.readouterr().out
        data = json.loads(output)
        assert "pr_number" in data
        assert "spam_probability" in data
        assert "classification" in data
        assert "triggered_signals" in data


class TestCliThresholds:
    def test_thresholds_display(self, capsys):
        main(["thresholds"])
        output = capsys.readouterr().out
        assert "LEGIT" in output
        assert "SUSPICIOUS" in output
        assert "SPAM" in output
        assert "0.25" in output
        assert "0.65" in output
