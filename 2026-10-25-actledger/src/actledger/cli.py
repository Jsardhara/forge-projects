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
from dataclasses import replace
from datetime import datetime, timezone
from typing import List, Optional

from .audit import FAIL_ON_ORDER, audit
from .chain import GENESIS_HASH, sha256_hex
from .export import ExportError, build_bundle, read_bundle, verify_bundle, write_bundle
from .bundleproof import ABSENT as BINDINGS_ABSENT
from .ledger import Ledger, LedgerError
from .manifest import (
    BindingError,
    ManifestError,
    append_binding,
    bare_hex,
    derive,
    load_binding_records,
    load_bindings,
)
from .models import ActionRecord, worst_severity
from .provenance import check_bindings


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
    record.add_argument(
        "--model-manifest",
        default="",
        help="a wsaudit manifest; its digest is recomputed here and recorded as measured",
    )
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
        "--verify-manifest",
        action="store_true",
        help="re-measure the manifest every bound digest came from",
    )
    audit_cmd.add_argument(
        "--fail-on", default="FLAG", type=str.upper, choices=list(FAIL_ON_ORDER)
    )

    export = sub.add_parser("export", help="write a self-contained audit bundle")
    export.add_argument("--ledger", required=True)
    export.add_argument("--out", required=True)
    export.add_argument(
        "--no-provenance",
        action="store_true",
        help="omit bindings deliberately; the bundle then says so and verifies as uncheckable",
    )

    verify_bundle_cmd = sub.add_parser("verify-bundle", help="verify a bundle offline")
    verify_bundle_cmd.add_argument("path")
    verify_bundle_cmd.add_argument("--json", action="store_true")

    tail = sub.add_parser("tail", help="print the last N records")
    tail.add_argument("--ledger", required=True)
    tail.add_argument("-n", type=int, default=5)

    binding = sub.add_parser(
        "verify-binding", help="which actions in this ledger ran on these exact weights"
    )
    binding.add_argument("--ledger", required=True)
    binding.add_argument("--manifest", required=True)
    binding.add_argument("--json", action="store_true")

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


def _resolve_digest(args):
    """The digest to record, and the manifest it was derived from (None if typed).

    Fail-closed: a manifest that does not agree with an explicitly supplied
    `--model-digest` is a usage error, and nothing is written. Preferring one silently
    is how a transcribed digest launders itself into a measured-looking record.
    """
    if not args.model_manifest:
        return args.model_digest, None

    if not args.model_id.strip():
        raise _UsageError(
            "actledger record: error: --model-manifest requires --model - a measured "
            "digest that names no model cannot be tied to an action"
        )
    derived = derive(args.model_manifest)
    supplied = args.model_digest.strip()
    if supplied and bare_hex(supplied) != derived.digest:
        raise _UsageError(
            "actledger record: error: --model-digest %s and manifest %s disagree "
            "(manifest digest %s) - nothing recorded"
            % (supplied[:20], args.model_manifest, derived.digest[:20])
        )
    return derived.tagged, derived


def _cmd_record(args) -> int:
    args_hash = sha256_hex(args.args_text) if args.args_text else ""
    model_digest, derived = _resolve_digest(args)
    record = ActionRecord(
        agent_id=args.agent,
        tool=args.tool,
        outcome=args.outcome,
        ts=args.ts or _now(),
        model_id=args.model_id,
        model_digest=model_digest,
        policy_version=args.policy_version,
        args_hash=args_hash,
        data_touched=tuple(args.data),
        verifier=args.verifier,
        approved_by=args.approved_by,
        approved_at=args.approved_at,
    )
    ts = record.ts
    entry = Ledger(args.ledger).append(record)
    if derived is not None:
        append_binding(args.ledger, entry.seq, derived, args.model_manifest, ts)
    print("recorded seq %d %s" % (entry.seq, entry.hash[:16]))
    return 0


def _cmd_verify(args) -> int:
    result = Ledger(args.ledger).verify()
    if args.json:
        print(json.dumps(_verification_payload(result), sort_keys=True))
        return 0 if result.ok else 1
    return _report_verification(result)


def _cmd_audit(args) -> int:
    entries = Ledger(args.ledger).entries()
    bindings = load_bindings(args.ledger)
    report = audit(entries, bindings)
    provenance = None
    if args.verify_manifest:
        provenance = check_bindings(entries, load_binding_records(args.ledger), args.ledger)
        findings = report.findings + provenance.findings
        report = replace(report, findings=findings, severity=worst_severity(findings))
    code = 0 if report.acceptable(args.fail_on) else 1
    if args.json:
        payload = report.to_dict()
        if provenance is not None:
            payload["provenance"] = provenance.to_dict()
        print(json.dumps(payload, sort_keys=True))
        return code
    for finding in report.findings:
        print("%s %s seq=%d %s" % (finding.code, finding.severity.value, finding.seq, finding.detail))
    print(
        "verdict: %s | actions: %d | unverified: %d | independently verified: %d"
        % (report.severity.value, report.total, report.unverified, report.independent_verified)
    )
    if provenance is not None:
        print(
            "provenance: %d checked | %d pass | %d mismatch | %d unmeasurable"
            % (
                provenance.checked,
                provenance.passed,
                provenance.mismatched,
                provenance.unmeasurable,
            )
        )
    return code


def _cmd_export(args) -> int:
    entries = Ledger(args.ledger).entries()
    bindings = None if args.no_provenance else load_binding_records(args.ledger)
    bundle = build_bundle(entries, bindings)
    write_bundle(args.out, bundle)
    carried = 0 if bundle["bindings"] is None else len(bundle["bindings"])
    print(
        "exported %d record(s), %d binding(s), provenance %s, head %s -> %s"
        % (
            bundle["count"],
            carried,
            bundle["provenance"],
            bundle["head_hash"][:16],
            args.out,
        )
    )
    return 0


def _bundle_payload(report) -> dict:
    return report.to_dict()


def _cmd_verify_bundle(args) -> int:
    report = verify_bundle(read_bundle(args.path))
    if args.json:
        print(json.dumps(_bundle_payload(report), sort_keys=True))
        return report.exit_code
    if report.ok:
        print("OK: %d record(s) verified, head %s" % (report.checked, report.head_hash[:16]))
    else:
        print("BREAK: %d record(s) walked, %d break(s)" % (report.checked, len(report.breaks)))
    for brk in report.breaks:
        print("  %s seq=%d %s" % (brk.code, brk.seq, brk.detail))

    proof = report.proof
    if report.state == BINDINGS_ABSENT or proof is None:
        print(
            "BINDINGS-ABSENT no bindings travelled with this artifact - provenance is "
            "not checkable here, which is not the same answer as clean"
        )
    else:
        print(
            "BINDINGS-PRESENT %d binding(s) carried | %d corroborated | %d mismatched | "
            "%d not checkable"
            % (
                len(report.bindings),
                proof.corroborated,
                proof.mismatched,
                proof.unmeasurable,
            )
        )
        if proof.declared_present:
            print(
                "audit: %s declared, %s earned by these records"
                % (
                    (proof.declared or {}).get("severity", "?"),
                    proof.recomputed.get("severity", "?"),
                )
            )
    print("state: %s" % report.state)
    return report.exit_code


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


def _cmd_verify_binding(args) -> int:
    """Which recorded actions ran on exactly these weights?

    Exit 0 = at least one action is bound to this manifest's digest, 1 = none is,
    2 = could not measure. It answers the auditor's question in the other direction from
    `audit`: not "is this row measured" but "what was done with these weights".
    """
    derived = derive(args.manifest)
    entries = Ledger(args.ledger).entries()
    bound = [entry for entry in entries if bare_hex(entry.record.model_digest) == derived.digest]
    if args.json:
        print(
            json.dumps(
                {
                    "model_digest": derived.tagged,
                    "manifest": os.path.abspath(args.manifest),
                    "tensor_count": derived.tensor_count,
                    "format": derived.format,
                    "scanned": len(entries),
                    "bound": len(bound),
                    "seqs": [entry.seq for entry in bound],
                },
                sort_keys=True,
            )
        )
    else:
        print(
            "%d action(s) in %s are bound to %s (%d tensor(s), %s)"
            % (len(bound), args.ledger, derived.tagged[:20], derived.tensor_count, derived.format)
        )
        for entry in bound:
            print("  seq=%d %s %s" % (entry.seq, entry.record.agent_id, entry.record.tool))
    return 0 if bound else 1


HANDLERS = {
    "record": _cmd_record,
    "verify": _cmd_verify,
    "audit": _cmd_audit,
    "export": _cmd_export,
    "verify-bundle": _cmd_verify_bundle,
    "tail": _cmd_tail,
    "verify-binding": _cmd_verify_binding,
}


def main(argv: Optional[List[str]] = None) -> int:
    try:
        args = _parser().parse_args(argv)
    except _UsageError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    try:
        return HANDLERS[args.command](args)
    except _UsageError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except (LedgerError, ExportError, ManifestError, BindingError, OSError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
