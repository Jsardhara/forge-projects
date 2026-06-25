"""Tests for prbouncer.signals — individual spam detection signals."""

from datetime import datetime, timezone, timedelta

import pytest

from prbouncer.models import AuthorProfile, PullRequest, SignalType
from prbouncer.signals import (
    signal_new_account,
    signal_no_linked_issue,
    signal_large_diff,
    signal_ai_slop,
    signal_generic_title,
    signal_rapid_fire,
    signal_low_engagement,
    signal_suspicious_files,
    signal_account_pattern,
)


def _author(age=365, username="contributor", **kwargs):
    defaults = {
        "followers": 10,
        "has_bio": True,
        "has_profile_pic": True,
    }
    defaults.update(kwargs)
    return AuthorProfile(username=username, account_age_days=age, **defaults)


def _pr(number=1, title="Fix bug in auth module", body="", author=None, **kwargs):
    if author is None:
        author = _author()
    defaults = {
        "additions": 10,
        "deletions": 5,
        "linked_issues": 1,
    }
    defaults.update(kwargs)
    return PullRequest(pr_number=number, title=title, body=body, author=author, **defaults)


# --- signal_new_account ---

class TestNewAccount:
    def test_today(self):
        pr = _pr(author=_author(age=0))
        s = signal_new_account(pr)
        assert s.triggered is True
        assert s.raw_score == 1.0

    def test_one_day(self):
        pr = _pr(author=_author(age=1))
        s = signal_new_account(pr)
        assert s.triggered is True
        assert s.raw_score > 0.7

    def test_week_old(self):
        pr = _pr(author=_author(age=7))
        s = signal_new_account(pr)
        assert s.triggered is True
        # At age=7, falls into the 7-30 bucket: 0.3 * (1 - (7-7)/23) = 0.3
        assert s.raw_score == pytest.approx(0.3)

    def test_month_old(self):
        pr = _pr(author=_author(age=30))
        s = signal_new_account(pr)
        assert s.triggered is False
        assert s.raw_score == 0.0

    def test_established(self):
        pr = _pr(author=_author(age=365))
        s = signal_new_account(pr)
        assert s.triggered is False
        assert s.raw_score == 0.0


# --- signal_no_linked_issue ---

class TestNoLinkedIssue:
    def test_has_linked_issue(self):
        pr = _pr(linked_issues=1)
        s = signal_no_linked_issue(pr)
        assert s.triggered is False

    def test_no_issue_ref_at_all(self):
        pr = _pr(title="Update code", body="Some changes", linked_issues=0)
        s = signal_no_linked_issue(pr)
        assert s.triggered is True
        assert s.raw_score > 0.0

    def test_manual_issue_ref_in_title(self):
        pr = _pr(title="Fixes #42", linked_issues=0)
        s = signal_no_linked_issue(pr)
        assert s.triggered is False

    def test_manual_issue_ref_in_body(self):
        pr = _pr(body="Closes #99", linked_issues=0)
        s = signal_no_linked_issue(pr)
        assert s.triggered is False


# --- signal_large_diff ---

class TestLargeDiff:
    def test_small_diff_new_account(self):
        pr = _pr(author=_author(age=5), additions=100, deletions=50)
        s = signal_large_diff(pr)
        assert s.triggered is False

    def test_large_diff_new_account(self):
        pr = _pr(author=_author(age=5), additions=1200, deletions=0)
        s = signal_large_diff(pr)
        assert s.triggered is True
        assert s.raw_score > 0.5

    def test_large_diff_established_ok(self):
        pr = _pr(author=_author(age=365), additions=2000, deletions=0)
        s = signal_large_diff(pr)
        assert s.triggered is False

    def test_very_large_diff_established(self):
        pr = _pr(author=_author(age=365), additions=15000, deletions=0)
        s = signal_large_diff(pr)
        assert s.triggered is True


# --- signal_ai_slop ---

class TestAiSlop:
    def test_clean_body(self):
        pr = _pr(body="This fixes the race condition in the worker pool.")
        s = signal_ai_slop(pr)
        assert s.triggered is False

    def test_single_slop_phrase(self):
        pr = _pr(body="I have analyzed the codebase and made improvements.")
        s = signal_ai_slop(pr)
        assert s.triggered is True
        assert s.raw_score >= 0.4

    def test_multiple_slop_phrases(self):
        pr = _pr(body="I have analyzed the codebase and this PR improves the codebase. I've refactored the code to enhance quality.")
        s = signal_ai_slop(pr)
        assert s.triggered is True
        assert s.raw_score > 0.6

    def test_as_an_ai(self):
        pr = _pr(body="As an AI, I suggest this change.")
        s = signal_ai_slop(pr)
        assert s.triggered is True

    def test_empty_body(self):
        pr = _pr(body="")
        s = signal_ai_slop(pr)
        assert s.triggered is False


# --- signal_generic_title ---

class TestGenericTitle:
    def test_specific_title(self):
        pr = _pr(title="Fix race condition in concurrent queue processor")
        s = signal_generic_title(pr)
        assert s.triggered is False

    def test_just_fix(self):
        pr = _pr(title="Fix")
        s = signal_generic_title(pr)
        assert s.triggered is True

    def test_update_file(self):
        pr = _pr(title="update main.py")
        s = signal_generic_title(pr)
        assert s.triggered is True

    def test_code_cleanup(self):
        pr = _pr(title="Code cleanup")
        s = signal_generic_title(pr)
        assert s.triggered is True

    def test_very_short_title(self):
        pr = _pr(title="WIP")
        s = signal_generic_title(pr)
        assert s.triggered is True

    def test_filepath_as_title(self):
        pr = _pr(title="src/utils/helpers.py")
        s = signal_generic_title(pr)
        assert s.triggered is True

    def test_reasonable_title(self):
        pr = _pr(title="Add timeout parameter to HTTP client")
        s = signal_generic_title(pr)
        assert s.triggered is False


# --- signal_rapid_fire ---

class TestRapidFire:
    def test_normal_contributor(self):
        pr = _pr()
        s = signal_rapid_fire(pr, recent_pr_count=1)
        assert s.triggered is False

    def test_moderate_activity(self):
        pr = _pr()
        s = signal_rapid_fire(pr, recent_pr_count=3)
        assert s.triggered is True
        assert s.raw_score > 0.0

    def test_high_activity(self):
        pr = _pr()
        s = signal_rapid_fire(pr, recent_pr_count=8)
        assert s.triggered is True
        assert s.raw_score > 0.5

    def test_extreme_activity(self):
        pr = _pr()
        s = signal_rapid_fire(pr, recent_pr_count=15)
        assert s.triggered is True
        assert s.raw_score == 1.0


# --- signal_low_engagement ---

class TestLowEngagement:
    def test_established_author_skipped(self):
        pr = _pr(author=_author(age=400), comment_count=0, review_count=0)
        s = signal_low_engagement(pr)
        assert s.triggered is False

    def test_new_author_no_engagement(self):
        pr = _pr(author=_author(age=10), comment_count=0, review_count=0)
        s = signal_low_engagement(pr)
        assert s.triggered is True

    def test_new_author_with_comments(self):
        pr = _pr(author=_author(age=10), comment_count=3, review_count=1)
        s = signal_low_engagement(pr)
        assert s.triggered is False


# --- signal_suspicious_files ---

class TestSuspiciousFiles:
    def test_code_files_only(self):
        pr = _pr(file_paths=("src/main.py", "src/utils.py", "tests/test_main.py"))
        s = signal_suspicious_files(pr)
        assert s.triggered is False

    def test_only_readme_new_account(self):
        pr = _pr(author=_author(age=5), file_paths=("README.md",), additions=50, linked_issues=0)
        s = signal_suspicious_files(pr)
        assert s.triggered is True
        assert s.raw_score >= 0.8

    def test_mixed_files(self):
        pr = _pr(file_paths=("src/main.py", "README.md", "docs/guide.md"))
        s = signal_suspicious_files(pr)
        assert s.raw_score > 0.0

    def test_no_file_paths(self):
        pr = _pr()
        s = signal_suspicious_files(pr)
        assert s.triggered is False

    def test_all_config_files(self):
        pr = _pr(author=_author(age=5), file_paths=("package.json", ".github/workflows/ci.yml", "README.md"), linked_issues=0)
        s = signal_suspicious_files(pr)
        assert s.triggered is True


# --- signal_account_pattern ---

class TestAccountPattern:
    def test_normal_username(self):
        pr = _pr(author=_author(username="johndoe", followers=15))
        s = signal_account_pattern(pr)
        assert s.triggered is False

    def test_generated_username(self):
        pr = _pr(author=_author(username="happy-84729", followers=0, has_bio=False, has_profile_pic=False))
        s = signal_account_pattern(pr)
        assert s.triggered is True

    def test_suspicious_underscore_numbers(self):
        pr = _pr(author=_author(username="dev_92837", followers=0, has_bio=False, has_profile_pic=False))
        s = signal_account_pattern(pr)
        assert s.triggered is True

    def test_no_bio_no_pic_low_followers(self):
        pr = _pr(author=_author(username="someone", followers=1, has_bio=False, has_profile_pic=False))
        s = signal_account_pattern(pr)
        assert s.triggered is True

    def test_has_bio_mitigates(self):
        pr = _pr(author=_author(username="someone", followers=1, has_bio=True, has_profile_pic=False))
        s = signal_account_pattern(pr)
        # May still trigger from other indicators but weight reduced
        # The key is it's not as strong as all three being bad
        if s.triggered:
            assert s.raw_score < 0.7
