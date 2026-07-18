"""Command-line interface for costrecon."""

import argparse
import csv
import sys
from typing import List

from .cur import parse_cur, summarize_by_service
from .idle import IdleDetector
from .models import Estimate, ResourceUtilization
from .reconcile import Reconciler
from .report import render_audit, render_idle, render_reconciliation


def _to_float(value, default=0.0):
    if value is None:
        return default
    s = str(value).strip().replace(",", "")
    if s == "" or s.lower() in ("nan", "n/a", "na"):
        return default
    try:
        return float(s)
    except ValueError:
        return default


def parse_estimates(path: str) -> List[Estimate]:
    out: List[Estimate] = []
    with open(path, "r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            if row is None:
                continue
            key = (row.get("key") or "").strip()
            if not key:
                continue
            out.append(
                Estimate(
                    key=key,
                    estimated_cost=_to_float(row.get("estimated_cost")),
                    note=(row.get("note") or "").strip(),
                )
            )
    return out


def parse_utilization(path: str) -> List[ResourceUtilization]:
    out: List[ResourceUtilization] = []
    with open(path, "r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            if row is None:
                continue
            rid = (row.get("resource_id") or "").strip()
            if not rid:
                continue
            up = row.get("utilization_pct")
            age = row.get("age_days")
            out.append(
                ResourceUtilization(
                    resource_id=rid,
                    rtype=(row.get("type") or "other").strip().lower(),
                    utilization_pct=_to_float(up) if (up not in (None, "", "n/a")) else None,
                    monthly_cost=_to_float(row.get("monthly_cost")),
                    region=(row.get("region") or "").strip(),
                    state=(row.get("state") or "").strip(),
                    age_days=_to_float(age) if (age not in (None, "", "n/a")) else None,
                )
            )
    return out


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="costrecon",
        description="Local AWS billing reconciliation: estimated-vs-actual variance "
        "+ idle/over-provisioned resource detection (zero dependencies).",
    )
    p.add_argument("--version", action="version", version="costrecon 0.1.0")
    sub = p.add_subparsers(dest="command", required=True)

    rec = sub.add_parser("reconcile", help="Reconcile estimates vs actual CUR spend.")
    rec.add_argument("--cur", required=True, help="Path to Cost & Usage Report CSV")
    rec.add_argument("--estimates", required=True, help="Path to estimates CSV (key,estimated_cost,note)")
    rec.add_argument("--threshold", type=float, default=5.0, help="Variance tolerance %% (default 5)")
    rec.add_argument("--key", choices=["service", "service_region"], default="service")
    rec.add_argument("--format", choices=["text", "json"], default="text")
    rec.add_argument("--strict", action="store_true", help="Exit 1 if any anomaly is found")

    idle = sub.add_parser("idle", help="Detect idle / over-provisioned resources.")
    idle.add_argument("--utilization", required=True, help="Path to utilization CSV")
    idle.add_argument("--idle-threshold", type=float, default=5.0, help="Utilization %% below which a compute resource is idle")
    idle.add_argument("--snapshot-max-age", type=float, default=30.0, help="Snapshot age (days) considered stale")
    idle.add_argument("--format", choices=["text", "json"], default="text")
    idle.add_argument("--strict", action="store_true", help="Exit 1 if any finding is found")

    audit = sub.add_parser("audit", help="Run reconcile + idle together.")
    audit.add_argument("--cur", required=True)
    audit.add_argument("--estimates", required=True)
    audit.add_argument("--utilization", required=True)
    audit.add_argument("--threshold", type=float, default=5.0)
    audit.add_argument("--idle-threshold", type=float, default=5.0)
    audit.add_argument("--snapshot-max-age", type=float, default=30.0)
    audit.add_argument("--key", choices=["service", "service_region"], default="service")
    audit.add_argument("--format", choices=["text", "json"], default="text")
    audit.add_argument("--strict", action="store_true")

    return p


def main(argv=None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "reconcile":
            items = parse_cur(args.cur)
            actuals = summarize_by_service(items, split_region=(args.key == "service_region"))
            report = Reconciler(args.threshold).reconcile(actuals, parse_estimates(args.estimates))
            print(render_reconciliation(report, args.format))
            return 1 if (args.strict and report.anomalies) else 0

        if args.command == "idle":
            detector = IdleDetector(args.idle_threshold, args.snapshot_max_age)
            report = detector.detect(parse_utilization(args.utilization))
            print(render_idle(report, args.format))
            return 1 if (args.strict and report.findings) else 0

        if args.command == "audit":
            items = parse_cur(args.cur)
            actuals = summarize_by_service(items, split_region=(args.key == "service_region"))
            recon = Reconciler(args.threshold).reconcile(actuals, parse_estimates(args.estimates))
            detector = IdleDetector(args.idle_threshold, args.snapshot_max_age)
            idle_report = detector.detect(parse_utilization(args.utilization))
            print(render_audit(recon, idle_report, args.format))
            flagged = bool(recon.anomalies) or bool(idle_report.findings)
            return 1 if (args.strict and flagged) else 0
    except FileNotFoundError as e:
        print(f"error: file not found: {e}", file=sys.stderr)
        return 2
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    parser.error("unknown command")
    return 2  # unreachable


if __name__ == "__main__":
    sys.exit(main())
