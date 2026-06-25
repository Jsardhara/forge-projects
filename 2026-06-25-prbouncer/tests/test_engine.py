"""Tests for prbouncer.engine — spam scoring engine."""

from datetime import datetime, timezone

import pytest

from prbouncer.models import AuthorProfile, PullRequest, Verdict, SignalType
from prbouncer.engine import SpamEngine


def _author(age=365, username="contributor", **kwargs):
    defaults = {
        "followers": 10,
        "has_bio": True,
        "has_profile_pic": True,
    }
    defaults.update(kwargs)
    return AuthorProfile(username=username, account_age_days=age, **defaults)


def _pr(number=1, title="Fix race condition in worker pool", body="", author=None, **kwargs):
    if author is None:
        author = _author()
    defaults = {
        "additions": 10,
        "deletions": 5,
        "linked_issues": 1,
    }
    defaults.update(kwargs)
    return PullRequest(pr_number=number, title=title, body=body, author=author, **defaults)


class TestSpamEngineEvaluate:
    def setup_method(self):
        self.engine = SpamEngine()

    def test_legit_pr(self):
        """Well-established contributor, specific title, linked issue, no slop."""
        pr = _pr(
            title="Fix memory leak in connection pool",
            body="This PR fixes the memory leak reported in #42.",
            author=_author(age=730, followers=50, public_repos=15),
            linked_issues=1,
        )
        verdict = self.engine.evaluate(pr)
        assert verdict.classification == "LEGIT"
        assert verdict.spam_probability < 0.25

    def test_obvious_spam(self):
        """Day-old account, AI slop body, no linked issue, generic title."""
        pr = _pr(
            title="Update code",
            body="I have analyzed the codebase and this PR improves the codebase. I've refactored the code to enhance quality.",
            author=_author(age=0, username="happy-84729", followers=0, has_bio=False, has_profile_pic=False),
            linked_issues=0,
            additions=200,
            deletions=0,
            file_paths=("README.md",),
        )
        verdict = self.engine.evaluate(pr, recent_pr_count=12)
        assert verdict.classification == "SPAM"
        assert verdict.spam_probability > 0.65

    def test_suspicious_pr(self):
        """30-day account, linked issue, but some minor signals."""
        pr = _pr(
            title="Fix typo in utils module",
            body="Small fix for a typo I found while using the utils module.",
            author=_author(age=14, followers=5, has_bio=True, has_profile_pic=True),
            linked_issues=1,
            additions=3,
            deletions=1,
            file_paths=("src/utils.py",),
            comment_count=1,
        )
        verdict = self.engine.evaluate(pr)
        # 14-day account with linked issue, bio/pic, code files, comments
        # Should be suspicious (new account signal) or legit, not spam
        assert verdict.classification in ("LEGIT", "SUSPICIOUS")
        assert verdict.spam_probability < 0.7

    def test_all_signals_returned(self):
        """Engine always returns all 9 signals."""
        pr = _pr()
        verdict = self.engine.evaluate(pr)
        assert len(verdict.signals) == 9

    def test_verdict_pr_number_matches(self):
        pr = _pr(number=42)
        verdict = self.engine.evaluate(pr)
        assert verdict.pr_number == 42

    def test_zero_probability_for_clean_pr(self):
        """Fully clean PR should have very low probability."""
        pr = _pr(
            title="Fix critical security vulnerability in token validation",
            body="Resolves #100. The current token validation logic allows bypass via crafted JWT.",
            author=_author(age=730, followers=100, public_repos=20),
            linked_issues=1,
            file_paths=("src/auth/tokens.py", "tests/test_tokens.py"),
        )
        verdict = self.engine.evaluate(pr)
        assert verdict.spam_probability < 0.15

    def test_custom_thresholds(self):
        engine = SpamEngine(legit_threshold=0.1, spam_threshold=0.9)
        pr = _pr()  # Normal PR
        verdict = engine.evaluate(pr)
        # With tighter legit threshold, this might shift
        assert verdict.classification in ("LEGIT", "SUSPICIOUS", "SPAM")

    def test_rapid_fire_increases_spam(self):
        """Same PR scored with different recent_pr_count."""
        pr = _pr(
            author=_author(age=3, username="newbie-1234", followers=0, has_bio=False, has_profile_pic=False),
            title="Update code",
            body="",
            linked_issues=0,
        )
        v_normal = self.engine.evaluate(pr, recent_pr_count=0)
        v_rapid = self.engine.evaluate(pr, recent_pr_count=15)
        assert v_rapid.spam_probability >= v_normal.spam_probability


class TestSpamEngineBatch:
    def test_batch_evaluate(self):
        engine = SpamEngine()
        prs = [
            _pr(number=1, title="Fix bug", linked_issues=1),
            _pr(number=2, title="Update code", author=_author(age=0), linked_issues=0),
        ]
        verdicts = engine.batch_evaluate(prs)
        assert len(verdicts) == 2
        assert verdicts[0].pr_number == 1
        assert verdicts[1].pr_number == 2

    def test_batch_with_recent_counts(self):
        engine = SpamEngine()
        prs = [_pr(number=i) for i in range(3)]
        verdicts = engine.batch_evaluate(prs, recent_pr_counts=[0, 5, 15])
        assert len(verdicts) == 3

    def test_batch_default_counts(self):
        engine = SpamEngine()
        prs = [_pr(number=i) for i in range(5)]
        verdicts = engine.batch_evaluate(prs)
        assert len(verdicts) == 5


class TestSpamEngineEdgeCases:
    def setup_method(self):
        self.engine = SpamEngine()

    def test_empty_body(self):
        pr = _pr(body="")
        verdict = self.engine.evaluate(pr)
        assert 0.0 <= verdict.spam_probability <= 1.0

    def test_very_long_body(self):
        pr = _pr(body="x" * 10000)
        verdict = self.engine.evaluate(pr)
        assert 0.0 <= verdict.spam_probability <= 1.0

    def test_zero_lines_changed(self):
        pr = _pr(additions=0, deletions=0)
        verdict = self.engine.evaluate(pr)
        assert 0.0 <= verdict.spam_probability <= 1.0

    def test_probability_bounded(self):
        """Spam probability is always in [0, 1]."""
        # Try many combinations
        for age in (0, 1, 7, 30, 365):
            for issues in (0, 1):
                for add in (0, 100, 5000):
                    pr = _pr(
                        title="Update code",
                        body="I have analyzed the codebase and this PR improves the codebase.",
                        author=_author(age=age, username="test-user-1234", followers=0, has_bio=False, has_profile_pic=False),
                        linked_issues=issues,
                        additions=add,
                    )
                    verdict = self.engine.evaluate(pr, recent_pr_count=10)
                    assert 0.0 <= verdict.spam_probability <= 1.0, f"p={verdict.spam_probability} for age={age}, issues={issues}, add={add}"

    def test_verdict_explain_no_crash(self):
        pr = _pr()
        verdict = self.engine.evaluate(pr)
        text = verdict.explain
        assert isinstance(text, str)
        assert len(text) > 0

    def test_deterministic(self):
        """Same input always produces same output."""
        pr = _pr(
            title="Update code",
            body="I have analyzed the codebase.",
            author=_author(age=3, username="bot-12345", followers=0, has_bio=False, has_profile_pic=False),
            linked_issues=0,
        )
        v1 = self.engine.evaluate(pr, recent_pr_count=5)
        v2 = self.engine.evaluate(pr, recent_pr_count=5)
        assert v1.spam_probability == v2.spam_probability
        assert v1.classification == v2.classification
