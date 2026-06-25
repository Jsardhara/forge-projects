"""Tests for prbouncer.models."""

from datetime import datetime, timezone

import pytest

from prbouncer.models import (
    AuthorProfile,
    PullRequest,
    SpamSignal,
    SignalType,
    Verdict,
)


class TestAuthorProfile:
    def test_is_new_true(self):
        profile = AuthorProfile(username="newbie", account_age_days=5)
        assert profile.is_new is True

    def test_is_new_false(self):
        profile = AuthorProfile(username="veteran", account_age_days=30)
        assert profile.is_new is False

    def test_is_new_boundary(self):
        profile = AuthorProfile(username="edge", account_age_days=7)
        assert profile.is_new is False

    def test_is_likely_bot_true(self):
        profile = AuthorProfile(
            username="bot-12345",
            account_age_days=15,
            has_bio=False,
            has_profile_pic=False,
            pr_count_total=20,
        )
        assert profile.is_likely_bot is True

    def test_is_likely_bot_has_bio(self):
        profile = AuthorProfile(
            username="contributor",
            account_age_days=15,
            has_bio=True,
            has_profile_pic=False,
            pr_count_total=20,
        )
        assert profile.is_likely_bot is False

    def test_is_likely_bot_old_account(self):
        profile = AuthorProfile(
            username="bot-12345",
            account_age_days=60,
            has_bio=False,
            has_profile_pic=False,
            pr_count_total=20,
        )
        assert profile.is_likely_bot is False

    def test_is_likely_bot_low_prs(self):
        profile = AuthorProfile(
            username="bot-12345",
            account_age_days=15,
            has_bio=False,
            has_profile_pic=False,
            pr_count_total=3,
        )
        assert profile.is_likely_bot is False

    def test_frozen(self):
        profile = AuthorProfile(username="test", account_age_days=10)
        with pytest.raises(AttributeError):
            profile.username = "changed"


class TestPullRequest:
    def _make_author(self, age=365):
        return AuthorProfile(username="contributor", account_age_days=age)

    def _make_pr(self, number=1, title="Fix bug", body="", **kwargs):
        defaults = {
            "author": self._make_author(),
            "additions": 10,
            "deletions": 5,
        }
        defaults.update(kwargs)
        return PullRequest(pr_number=number, title=title, body=body, **defaults)

    def test_total_lines(self):
        pr = self._make_pr(additions=100, deletions=50)
        assert pr.total_lines == 150

    def test_has_issue_ref_linked(self):
        pr = self._make_pr(linked_issues=1)
        assert pr.has_issue_ref is True

    def test_has_issue_ref_title(self):
        pr = self._make_pr(title="Fixes #42")
        assert pr.has_issue_ref is True

    def test_has_issue_ref_body(self):
        pr = self._make_pr(body="Resolves #99 by doing X")
        assert pr.has_issue_ref is True

    def test_has_issue_ref_none(self):
        pr = self._make_pr(title="Update code", body="Some changes")
        assert pr.has_issue_ref is False

    def test_default_timestamp_is_utc(self):
        pr = self._make_pr()
        assert pr.created_at.tzinfo is not None

    def test_frozen(self):
        pr = self._make_pr()
        with pytest.raises(AttributeError):
            pr.title = "changed"


class TestSpamSignal:
    def test_contribution_triggered(self):
        signal = SpamSignal(
            signal_type=SignalType.NEW_ACCOUNT,
            weight=0.20,
            triggered=True,
            evidence="test",
            raw_score=0.8,
        )
        assert signal.contribution == pytest.approx(0.16)

    def test_contribution_not_triggered(self):
        signal = SpamSignal(
            signal_type=SignalType.NEW_ACCOUNT,
            weight=0.20,
            triggered=False,
            evidence="test",
            raw_score=0.8,
        )
        assert signal.contribution == 0.0


class TestVerdict:
    def _make_verdict(self, p=0.5):
        return Verdict(pr_number=1, spam_probability=p)

    def test_classification_legit(self):
        v = self._make_verdict(p=0.1)
        assert v.classification == "LEGIT"

    def test_classification_suspicious(self):
        v = self._make_verdict(p=0.5)
        assert v.classification == "SUSPICIOUS"

    def test_classification_spam(self):
        v = self._make_verdict(p=0.8)
        assert v.classification == "SPAM"

    def test_classification_boundary_legit(self):
        v = self._make_verdict(p=0.24)
        assert v.classification == "LEGIT"

    def test_classification_boundary_suspicious_low(self):
        v = self._make_verdict(p=0.25)
        assert v.classification == "SUSPICIOUS"

    def test_classification_boundary_suspicious_high(self):
        v = self._make_verdict(p=0.65)
        assert v.classification == "SUSPICIOUS"

    def test_classification_boundary_spam(self):
        v = self._make_verdict(p=0.66)
        assert v.classification == "SPAM"

    def test_triggered_signals(self):
        s1 = SpamSignal(SignalType.NEW_ACCOUNT, 0.2, True, "x", 0.8)
        s2 = SpamSignal(SignalType.AI_SLOP_MARKERS, 0.25, False, "y", 0.0)
        s3 = SpamSignal(SignalType.GENERIC_TITLE, 0.12, True, "z", 0.5)
        v = Verdict(pr_number=1, spam_probability=0.5, signals=(s1, s2, s3))
        assert len(v.triggered_signals) == 2

    def test_explain_format(self):
        s1 = SpamSignal(SignalType.NEW_ACCOUNT, 0.2, True, "Account is 3 days old", 0.8)
        v = Verdict(pr_number=42, spam_probability=0.7, signals=(s1,))
        text = v.explain
        assert "PR #42" in text
        assert "SPAM" in text
        assert "new_account" in text

    def test_explain_no_signals(self):
        v = Verdict(pr_number=1, spam_probability=0.1)
        assert "no signals triggered" in v.explain
