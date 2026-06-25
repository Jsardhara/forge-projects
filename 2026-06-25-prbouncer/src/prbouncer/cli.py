"""CLI for PRBouncer — PR spam detection engine."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone

from prbouncer.models import AuthorProfile, PullRequest
from prbouncer.engine import SpamEngine


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="prbouncer",
        description="PR spam detection engine for open source maintainers",
    )
    sub = parser.add_subparsers(dest="command")

    # analyze command
    analyze = sub.add_parser("analyze", help="Analyze a single PR for spam signals")
    analyze.add_argument("--pr", type=int, required=True, help="PR number")
    analyze.add_argument("--title", required=True, help="PR title")
    analyze.add_argument("--body", default="", help="PR body/description")
    analyze.add_argument("--author", required=True, help="Author username")
    analyze.add_argument("--account-age", type=int, required=True, help="Account age in days")
    analyze.add_argument("--followers", type=int, default=0, help="Author followers")
    analyze.add_argument("--additions", type=int, default=0, help="Lines added")
    analyze.add_argument("--deletions", type=int, default=0, help="Lines deleted")
    analyze.add_argument("--changed-files", type=int, default=0, help="Number of changed files")
    analyze.add_argument("--linked-issues", type=int, default=0, help="Linked issue count")
    analyze.add_argument("--recent-prs", type=int, default=0, help="Author's recent PR count")
    analyze.add_argument("--files", nargs="*", default=[], help="Changed file paths")
    analyze.add_argument("--json", action="store_true", help="Output as JSON")

    # batch command (reads JSON from stdin)
    batch = sub.add_parser("batch", help="Batch analyze PRs from JSON stdin")
    batch.add_argument("--json", action="store_true", help="Output as JSON (always true for batch)")

    # thresholds command
    thresholds = sub.add_parser("thresholds", help="Show classification thresholds")

    args = parser.parse_args(argv)

    if args.command == "analyze":
        _cmd_analyze(args)
    elif args.command == "batch":
        _cmd_batch(args)
    elif args.command == "thresholds":
        _cmd_thresholds()
    else:
        parser.print_help()
        sys.exit(1)


def _cmd_analyze(args: argparse.Namespace) -> None:
    author = AuthorProfile(
        username=args.author,
        account_age_days=args.account_age,
        followers=args.followers,
    )
    pr = PullRequest(
        pr_number=args.pr,
        title=args.title,
        body=args.body,
        author=author,
        additions=args.additions,
        deletions=args.deletions,
        changed_files=args.changed_files,
        linked_issues=args.linked_issues,
        file_paths=tuple(args.files),
    )
    engine = SpamEngine()
    verdict = engine.evaluate(pr, recent_pr_count=args.recent_prs)

    if args.json:
        output = {
            "pr_number": verdict.pr_number,
            "spam_probability": round(verdict.spam_probability, 4),
            "classification": verdict.classification,
            "label": verdict.label,
            "triggered_signals": [
                {
                    "type": s.signal_type.value,
                    "evidence": s.evidence,
                    "raw_score": round(s.raw_score, 3),
                    "weight": s.weight,
                }
                for s in verdict.triggered_signals
            ],
        }
        print(json.dumps(output, indent=2))
    else:
        print(verdict.explain)


def _cmd_batch(args: argparse.Namespace) -> None:
    data = json.load(sys.stdin)
    engine = SpamEngine()

    results = []
    for item in data:
        author = AuthorProfile(
            username=item.get("author", "unknown"),
            account_age_days=item.get("account_age_days", 365),
            followers=item.get("followers", 0),
        )
        pr = PullRequest(
            pr_number=item.get("pr_number", 0),
            title=item.get("title", ""),
            body=item.get("body", ""),
            author=author,
            additions=item.get("additions", 0),
            deletions=item.get("deletions", 0),
            linked_issues=item.get("linked_issues", 0),
            file_paths=tuple(item.get("file_paths", [])),
        )
        verdict = engine.evaluate(pr, recent_pr_count=item.get("recent_prs", 0))
        results.append({
            "pr_number": verdict.pr_number,
            "spam_probability": round(verdict.spam_probability, 4),
            "classification": verdict.classification,
            "triggered_count": len(verdict.triggered_signals),
        })

    print(json.dumps(results, indent=2))


def _cmd_thresholds() -> None:
    print("PRBouncer Classification Thresholds:")
    print(f"  LEGIT:      p < 0.25")
    print(f"  SUSPICIOUS: 0.25 <= p <= 0.65")
    print(f"  SPAM:       p > 0.65")


if __name__ == "__main__":
    main()
