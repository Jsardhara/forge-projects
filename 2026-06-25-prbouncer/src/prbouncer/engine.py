"""Spam scoring engine — combines individual signals into a final verdict."""

from __future__ import annotations

from typing import Optional

from prbouncer.models import PullRequest, Verdict, SpamSignal
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


class SpamEngine:
    """Multi-signal heuristic spam detection engine.

    Evaluates a PullRequest against all configured signals and produces
    a Verdict with a spam probability score (0.0–1.0).

    Usage:
        engine = SpamEngine()
        verdict = engine.evaluate(pr, recent_pr_count=3)
        print(verdict.classification)  # "LEGIT", "SUSPICIOUS", or "SPAM"
    """

    def __init__(
        self,
        legit_threshold: float = 0.25,
        spam_threshold: float = 0.65,
    ):
        self.legit_threshold = legit_threshold
        self.spam_threshold = spam_threshold

    def evaluate(
        self,
        pr: PullRequest,
        recent_pr_count: int = 0,
    ) -> Verdict:
        """Evaluate a PR and produce a spam verdict.

        Args:
            pr: The pull request to evaluate.
            recent_pr_count: Number of recent PRs by the same author (for rapid-fire detection).

        Returns:
            Verdict with spam probability, all signals, and classification.
        """
        signals: list[SpamSignal] = [
            signal_new_account(pr),
            signal_no_linked_issue(pr),
            signal_large_diff(pr),
            signal_ai_slop(pr),
            signal_generic_title(pr),
            signal_rapid_fire(pr, recent_pr_count=recent_pr_count),
            signal_low_engagement(pr),
            signal_suspicious_files(pr),
            signal_account_pattern(pr),
        ]

        # Weighted combination: sum of (weight * raw_score) for triggered signals
        # divided by sum of all weights for normalization
        total_weighted = sum(s.contribution for s in signals)
        total_possible_weight = sum(s.weight for s in signals if s.triggered)

        if total_possible_weight > 0:
            spam_probability = min(1.0, total_weighted / total_possible_weight)
        else:
            spam_probability = 0.0

        # Classify
        label = self._classify(spam_probability)

        return Verdict(
            pr_number=pr.pr_number,
            spam_probability=spam_probability,
            signals=tuple(signals),
            label=label,
        )

    def _classify(self, probability: float) -> str:
        if probability < self.legit_threshold:
            return "LEGIT"
        elif probability > self.spam_threshold:
            return "SPAM"
        else:
            return "SUSPICIOUS"

    def batch_evaluate(
        self,
        prs: list[PullRequest],
        recent_pr_counts: Optional[list[int]] = None,
    ) -> list[Verdict]:
        """Evaluate multiple PRs at once.

        Args:
            prs: List of pull requests to evaluate.
            recent_pr_counts: Optional per-PR recent PR counts. Defaults to 0.

        Returns:
            List of Verdicts in same order as input.
        """
        if recent_pr_counts is None:
            recent_pr_counts = [0] * len(prs)

        return [
            self.evaluate(pr, recent_pr_count=count)
            for pr, count in zip(prs, recent_pr_counts)
        ]
