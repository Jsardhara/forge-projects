#!/usr/bin/env python3
"""Seed an evidence ledger from a Hermes kanban database (read-only).

    PYTHONPATH=src python3 scripts/from_hermes_kanban.py \
        --db ~/.hermes/kanban.db --out actions.jsonl

Every `task_runs` row becomes one ledger record. Nothing is invented: fields the kanban
never recorded (named verifier, policy version, weights digest) are left empty so the
audit counts them instead of a green tick papering over them.
"""

import argparse
import sys

from actledger.audit import audit
from actledger.ledger import Ledger, LedgerError
from actledger.sources import SourceError, records_from_kanban


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--db", required=True, help="path to kanban.db")
    parser.add_argument("--out", required=True, help="ledger file to create")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--profile", default=None)
    parser.add_argument(
        "--replace",
        action="store_true",
        help="start from an empty ledger (refuses by default when the file exists)",
    )
    args = parser.parse_args(argv)

    try:
        records = records_from_kanban(args.db, limit=args.limit, profile=args.profile)
    except SourceError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2

    ledger = Ledger(args.out)
    if ledger.exists() and not args.replace:
        print(
            "error: %s already exists — pass --replace to start a new ledger" % args.out,
            file=sys.stderr,
        )
        return 2
    if ledger.exists():
        import os

        os.remove(args.out)
        if os.path.exists(ledger.head_path):
            os.remove(ledger.head_path)

    for record in records:
        ledger.append(record)

    verified = ledger.verify()
    report = audit(ledger.entries())
    print("imported %d run(s) from %s" % (len(records), args.db))
    print("chain: %s (%d records, head %s)" % ("OK" if verified.ok else "BROKEN", verified.checked, verified.head_hash[:16]))
    print(
        "responsibility: verdict %s | unverified %d/%d | independently verified %d"
        % (report.severity.value, report.unverified, report.total, report.independent_verified)
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
