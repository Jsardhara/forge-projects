"""Command line surface.

Exit codes are the contract a CI gate or an auditor scripts against:
  0 — clean
  1 — findings, or a chain that does not verify
  2 — usage error, missing file, unreadable input
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from typing import List, Optional

from .audit import FAIL_ON_ORDER, audit
from .chain import GENESIS_HASH, sha256_hex
from .export import ExportError, build_bundle, read_bundle, verify_bundle, write_bundle
from .ledger import Ledger, LedgerError
from .models import ActionRecord


class _UsageError(Exception):
    pass


class _Parser(argparse.ArgumentParser):
    def error(self, message):  # pragma: no cover - exercised through main()
        raise _UsageError("%s: error: %s" % (self.prog, message))


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parser() -> _Parser:
    parser = _Parser(prog="actledger", description="Agent action evidence ledger")
    sub = parser.add_subparsers(dest="command", required=True, parser_class=_Parser)

    record = sub.add_parser("record", help="append one action to the ledger")
    record.add_argument("--ledger", required=True)
    record.add_argument("--agent", required=True)
    record.add_argument("--tool", required=True)
    record.add_argument("--outcome", required=True)
    record.add_argument("--ts", default="")
    record.add_argument("--model", default="", dest="model_id")
    record.add_argument("--model-digest", default="")
    record.add_argument("--policy", default="", dest="policy_version")
    record.add_argument("--args-text", default="", help="raw arguments; stored as a hash")
    record.add_argument("--data", action="append", default=[], help="path or dataset touched")
    record.add_argument("--verifier", default="", help="who is assigned to check this action")
    record.add_argument("--approved-by", default="")
    record.add_argument("--approved-at", default="")

    verify = sub.add_parser("verify", help="walk the chain")
    verify.add_argument("--ledger", required=True)
    verify.add_argument("--json", action="store_true")

    audit_cmd = sub.add_parser("audit", help="report actions with no named verifier")
    audit_cmd.add_argument("--ledger", required=True)
    audit_cmd.add_argument("--json", action="store_true")
    audit_cmd.add_argument(
        "--fail-on", default="FLAG", type=str.upper, choices=list(FAIL_ON_ORDER)
    )

    export = sub.add_parser("export", help="write a self-contained audit bundle")
    export.add_argument("--ledger", required=True)
    export.add_argument("--out", required=True)

    verify_bundle_cmd = sub.add_parser("verify-bundle", help="verify a bundle offline")
    verify_bundle_cmd.add_argument("path")
    verify_bundle_cmd.add_argument("--json", action="store_true")

    tail = sub.add_parser("tail", help="print the last N records")
    tail.add_argument("--ledger", required=True)
    tail.add_argument("-n", type=int, default=5)

    return parser


def _verification_payload(result) -> dict:
    return {
        "ok": result.ok,
        "checked": result.checked,
        "head_hash": result.head_hash,
        "breaks": [
            {"code": brk.code, "seq": brk.seq, "detail": brk.detail} for brk in result.breaks
        ],
    }


def _report_verification(result) -> int:
    if result.ok:
        print("OK: %d record(s) verified, head %s" % (result.checked, result.head_hash[:16]))
        return 0
    print("BREAK: %d record(s) walked, %d break(s)" % (result.checked, len(result.breaks)))
    for brk in result.breaks:
        print("  %s seq=%d %s" % (brk.code, brk.seq, brk.detail))
    return 1


def _cmd_record(args) -> int:
    args_hash = sha256_hex(args.args_text) if args.args_text else ""
    record = ActionRecord(
        agent_id=args.agent,
        tool=args.tool,
        outcome=args.outcome,
        ts=args.ts or _now(),
        model_id=args.model_id,
        model_digest=args.model_digest,
        policy_version=args.policy_version,
        args_hash=args_hash,
        data_touched=tuple(args.data),
        verifier=args.verifier,
        approved_by=args.approved_by,
        approved_at=args.approved_at,
    )
    entry = Ledger(args.ledger).append(record)
    print("recorded seq %d %s" % (entry.seq, entry.hash[:16]))
    return 0


def _cmd_verify(args) -> int:
    result = Ledger(args.ledger).verify()
    if args.json:
        print(json.dumps(_verification_payload(result), sort_keys=True))
        return 0 if result.ok else 1
    return _report_verification(result)


def _cmd_audit(args) -> int:
    report = audit(Ledger(args.ledger).entries())
    code = 0 if report.acceptable(args.fail_on) else 1
    if args.json:
        print(json.dumps(report.to_dict(), sort_keys=True))
        return code
    for finding in report.findings:
        print("%s %s seq=%d %s" % (finding.code, finding.severity.value, finding.seq, finding.detail))
    print(
        "verdict: %s | actions: %d | unverified: %d | independently verified: %d"
        % (report.severity.value, report.total, report.unverified, report.independent_verified)
    )
    return code


def _cmd_export(args) -> int:
    bundle = build_bundle(Ledger(args.ledger).entries())
    write_bundle(args.out, bundle)
    print("exported %d record(s), head %s -> %s" % (bundle["count"], bundle["head_hash"][:16], args.out))
    return 0


def _cmd_verify_bundle(args) -> int:
    result = verify_bundle(read_bundle(args.path))
    if args.json:
        print(json.dumps(_verification_payload(result), sort_keys=True))
        return 0 if result.ok else 1
    return _report_verification(result)


def _cmd_tail(args) -> int:
    if args.n < 0:
        raise _UsageError("actledger: error: -n must be >= 0")
    entries = Ledger(args.ledger).entries()[-args.n :] if args.n else []
    for entry in entries:
        record = entry.record
        print(
            "seq=%d agent=%s tool=%s outcome=%s verifier=%s data=%s"
            % (
                entry.seq,
                record.agent_id,
                record.tool,
                record.outcome,
                record.verifier or "-",
                ",".join(record.data_touched) or "-",
            )
        )
    return 0


HANDLERS = {
    "record": _cmd_record,
    "verify": _cmd_verify,
    "audit": _cmd_audit,
    "export": _cmd_export,
    "verify-bundle": _cmd_verify_bundle,
    "tail": _cmd_tail,
}


def main(argv: Optional[List[str]] = None) -> int:
    try:
        args = _parser().parse_args(argv)
    except _UsageError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    try:
        return HANDLERS[args.command](args)
    except (LedgerError, ExportError, OSError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
