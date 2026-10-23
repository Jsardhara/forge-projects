"""pubgate CLI — fail-closed pre-install gate.

``pubgate record`` hashes an audited source tree.
``pubgate verify`` refuses an artifact that does not correspond to it.

Exit codes: 0 PASS · 1 violations found · 2 unusable input (never a silent pass).
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional

from pubgate.engine import (
    PubgateError,
    Violation,
    exit_code,
    load_manifest,
    source_manifest,
    verify_record,
    verify_source,
)

PASS = "PASS"
FAIL = "FAIL"


def _report(label: str, violations: List[Violation]) -> None:
    status = PASS if not violations else FAIL
    print("{} {}: {}".format(label, status, len(violations)))
    for v in violations:
        print("  - {}".format(v))


def _cmd_record(args: argparse.Namespace) -> int:
    man = source_manifest(args.source, name=args.name, version=args.version)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(man, fh, indent=2, sort_keys=True)
        fh.write("\n")
    print("RECORDED {} files from {}".format(man["file_count"], args.source))
    print("  digest: {}".format(man["digest"]))
    print("  out:    {}".format(args.out))
    return 0


def _cmd_verify(args: argparse.Namespace) -> int:
    violations: List[Violation] = []
    rec_violations = verify_record(args.wheel)
    _report("RECORD", rec_violations)
    violations.extend(rec_violations)

    if args.manifest:
        man = load_manifest(args.manifest)
        src = verify_source(args.wheel, man)
        _report("SOURCE", src)
        violations.extend(src)
    else:
        print("SOURCE SKIPPED: no --manifest given; artifact is self-consistent "
              "but NOT proven to correspond to any audited source")

    code = exit_code(violations)
    print("{} {} ({} violation{})".format(
        PASS if code == 0 else FAIL,
        args.wheel,
        len(violations),
        "" if len(violations) == 1 else "s",
    ))
    return code


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="pubgate",
        description="Verify a published Python artifact corresponds to its audited source.",
    )
    sub = p.add_subparsers(dest="command", required=True)

    rec = sub.add_parser("record", help="hash an audited source tree into a manifest")
    rec.add_argument("--source", required=True, help="audited source directory")
    rec.add_argument("--name", default=None, help="expected distribution name")
    rec.add_argument("--version", default=None, help="expected version to bind")
    rec.add_argument("--out", required=True, help="manifest path to write")
    rec.set_defaults(func=_cmd_record)

    ver = sub.add_parser("verify", help="check an artifact against a manifest")
    ver.add_argument("--wheel", required=True, help=".whl artifact to verify")
    ver.add_argument("--manifest", default=None, help="manifest from `record`")
    ver.set_defaults(func=_cmd_verify)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except PubgateError as exc:
        print("{} {}".format(FAIL, exc), file=sys.stderr)
        return 2
    except OSError as exc:
        print("{} I/O error: {}".format(FAIL, exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
