"""feescope CLI -- `scan` (human/JSON) and `check` (CI gate).

Input is a CSV or JSON file of billing line items, or stdin via `-`.

CSV columns (header required):
    line_id,description,amount,verified,category,attached_to

JSON is either:
  - an array of item objects (same keys), or
  - an object: {"invoice_id": str, "expected_total": float|null, "items":[...]}
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from typing import List, Optional, Tuple

from .engine import FeeScopeScanner, ScanConfig
from .models import FeeItem, InvoiceReport, Severity


def _f_opt(raw: Optional[str]) -> Optional[float]:
    if raw is None:
        return None
    s = raw.strip()
    if s == "":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def load_items_csv(path: str) -> Tuple[List[FeeItem], str, Optional[float]]:
    items: List[FeeItem] = []
    invoice_id = "invoice"
    expected_total: Optional[float] = None
    if path == "-":
        stream = sys.stdin
    else:
        stream = open(path, "r", encoding="utf-8", newline="")
    with stream:
        reader = csv.DictReader(stream)
        for row in reader:
            items.append(
                FeeItem(
                    line_id=(row.get("line_id") or "").strip(),
                    description=(row.get("description") or "").strip(),
                    amount=float(row.get("amount") or 0.0),
                    category=(row.get("category") or "media").strip() or "media",
                    verified=_f_opt(row.get("verified")),
                    attached_to=((row.get("attached_to") or "").strip() or None),
                )
            )
    return items, invoice_id, expected_total


def load_items_json(path: str) -> Tuple[List[FeeItem], str, Optional[float]]:
    if path == "-":
        data = json.load(sys.stdin)
    else:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    if isinstance(data, dict):
        invoice_id = str(data.get("invoice_id") or "invoice")
        expected_total = _f_opt(str(data.get("expected_total")) if data.get("expected_total") is not None else None)
        rows = data.get("items") or []
    else:
        invoice_id, expected_total, rows = "invoice", None, data
    items: List[FeeItem] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        items.append(
            FeeItem(
                line_id=str(row.get("line_id") or ""),
                description=str(row.get("description") or ""),
                amount=float(row.get("amount") or 0.0),
                category=str(row.get("category") or "media") or "media",
                verified=_f_opt(str(row["verified"])) if row.get("verified") is not None else None,
                attached_to=(str(row["attached_to"]) if row.get("attached_to") else None),
            )
        )
    return items, invoice_id, expected_total


def load_items(path: str) -> Tuple[List[FeeItem], str, Optional[float]]:
    if path != "-" and not path.lower().endswith((".csv", ".txt")):
        # assume JSON
        return load_items_json(path)
    # default to JSON for stdin (more flexible); decide by peek if file
    if path == "-":
        # try JSON, fall back to CSV
        saved = sys.stdin.read()
        import io

        sys.stdin = io.StringIO(saved)
        first = saved.lstrip()[:1]
        if first in "{[":
            return load_items_json("-")
        return load_items_csv("-")
    with open(path, "r", encoding="utf-8", newline="") as probe:
        first = probe.read(1)
    if first in "{[":
        return load_items_json(path)
    return load_items_csv(path)


def _render_human(report: InvoiceReport) -> str:
    lines = [
        f"invoice   {report.invoice_id}",
        f"verdict   {report.verdict.value}  {report.score:.0f}/100",
        f"billed    ${report.total_billed:,.2f}",
        f"fees      ${report.total_fees:,.2f}  ({report.fee_ratio * 100:.1f}%)",
    ]
    if report.findings:
        lines.append("findings")
        for f in report.findings:
            severity = f.severity.value
            loc = f" [{f.line_id}]" if f.line_id else ""
            lines.append(f"  {severity:<4} {f.code}{loc}: {f.detail}")
    else:
        lines.append("findings  (none)")
    return "\n".join(lines)


def _run_scan(args: argparse.Namespace) -> int:
    try:
        items, invoice_id, expected_total = load_items(args.path)
    except Exception as exc:  # noqa: BLE001
        print(f"feescope: failed to read input: {exc}", file=sys.stderr)
        return 2
    cfg = ScanConfig(
        tolerance=args.tolerance,
        flag_tolerance=args.flag_tolerance,
        max_fee_ratio=args.max_fee_ratio,
    )
    report = FeeScopeScanner(cfg).scan(items, invoice_id, expected_total)
    if args.json:
        print(json.dumps(_report_dict(report), separators=(",", ":")))
    else:
        print(_render_human(report))
    return 0


def _run_check(args: argparse.Namespace) -> int:
    try:
        items, invoice_id, expected_total = load_items(args.path)
    except Exception as exc:  # noqa: BLE001
        print(f"feescope: failed to read input: {exc}", file=sys.stderr)
        return 2
    cfg = ScanConfig(
        tolerance=args.tolerance,
        flag_tolerance=args.flag_tolerance,
        max_fee_ratio=args.max_fee_ratio,
    )
    report = FeeScopeScanner(cfg).scan(items, invoice_id, expected_total)
    print(_render_human(report))
    fails = report.verdict.value != "CLEAR" or report.score >= args.threshold
    return 1 if fails else 0


def _report_dict(report: InvoiceReport) -> dict:
    return {
        "invoice_id": report.invoice_id,
        "verdict": report.verdict.value,
        "score": round(report.score, 1),
        "total_billed": round(report.total_billed, 2),
        "total_fees": round(report.total_fees, 2),
        "fee_ratio": round(report.fee_ratio, 4),
        "findings": [
            {
                "code": f.code,
                "severity": f.severity.value,
                "line_id": f.line_id,
                "detail": f.detail,
            }
            for f in report.findings
        ],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="feescope",
        description="Ad-spend surcharge & fee-opaqueness audit scanner",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    scan_parser = sub.add_parser("scan", help="audit an invoice (human or JSON)")
    scan_parser.add_argument("path", help="CSV/JSON file or '-' for stdin")
    scan_parser.add_argument("--json", action="store_true", help="emit JSON")
    scan_parser.add_argument("--tolerance", type=float, default=0.005)
    scan_parser.add_argument("--flag-tolerance", type=float, default=0.05)
    scan_parser.add_argument("--max-fee-ratio", type=float, default=0.20)

    check_parser = sub.add_parser("check", help="CI gate (exit 1 on non-CLEAR)")
    check_parser.add_argument("path", help="CSV/JSON file or '-' for stdin")
    check_parser.add_argument("--threshold", type=float, default=60.0)
    check_parser.add_argument("--tolerance", type=float, default=0.005)
    check_parser.add_argument("--flag-tolerance", type=float, default=0.05)
    check_parser.add_argument("--max-fee-ratio", type=float, default=0.20)
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if args.cmd == "scan":
        return _run_scan(args)
    return _run_check(args)


if __name__ == "__main__":
    sys.exit(main())