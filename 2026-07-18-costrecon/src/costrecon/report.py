"""Text / JSON renderers for costrecon reports."""

import json
from typing import List

from .models import IdleReport, ReconciliationReport, Variance


def _money(v: float) -> str:
    return f"${v:,.2f}"


def render_reconciliation(report: ReconciliationReport, fmt: str = "text") -> str:
    if fmt == "json":
        return json.dumps(_recon_dict(report), indent=2)
    return _recon_text(report)


def render_idle(report: IdleReport, fmt: str = "text") -> str:
    if fmt == "json":
        return json.dumps(_idle_dict(report), indent=2)
    return _idle_text(report)


def render_audit(
    recon: ReconciliationReport, idle: IdleReport, fmt: str = "text"
) -> str:
    if fmt == "json":
        return json.dumps(
            {"reconciliation": _recon_dict(recon), "idle": _idle_dict(idle)}, indent=2
        )
    parts = [_recon_text(recon), "", _idle_text(idle)]
    return "\n".join(parts)


# --- internals ---------------------------------------------------------------

def _recon_dict(r: ReconciliationReport) -> dict:
    return {
        "total_estimated": r.total_estimated,
        "total_actual": r.total_actual,
        "total_delta": round(r.total_actual - r.total_estimated, 4),
        "anomaly_count": len(r.anomalies),
        "unestimated_services": list(r.unestimated_services),
        "by_key": [_var_dict(v) for v in r.by_key],
        "generated_at": r.generated_at.isoformat(),
    }


def _var_dict(v: Variance) -> dict:
    return {
        "key": v.key,
        "estimated": v.estimated,
        "actual": v.actual,
        "delta": v.delta,
        "pct": v.pct,
        "classification": v.classification,
        "anomaly": v.anomaly,
    }


def _idle_dict(r: IdleReport) -> dict:
    return {
        "total_cost": r.total_cost,
        "total_savings": r.total_savings,
        "finding_count": len(r.findings),
        "findings": [
            {
                "resource_id": f.resource_id,
                "type": f.rtype,
                "reason": f.reason,
                "severity": f.severity,
                "monthly_cost": f.monthly_cost,
                "estimated_savings": f.estimated_savings,
            }
            for f in r.findings
        ],
        "generated_at": r.generated_at.isoformat(),
    }


def _recon_text(r: ReconciliationReport) -> str:
    delta = round(r.total_actual - r.total_estimated, 2)
    pct = ""
    if r.total_estimated:
        pct = f" ({(delta / r.total_estimated * 100):.1f}%)"
    lines = [
        "COST RECONCILIATION",
        f"  Total estimated : {_money(r.total_estimated)}",
        f"  Total actual    : {_money(r.total_actual)}",
        f"  Delta           : {_money(delta)}{pct}",
        "",
    ]
    if r.anomalies:
        lines.append(f"ANOMALIES ({len(r.anomalies)}) -- variance > tolerance:")
        for v in r.anomalies:
            pct_s = f"{v.pct:+.1f}%" if v.pct is not None else "n/a"
            lines.append(
                f"  [{v.classification}] {v.key}\n"
                f"      est {_money(v.estimated)} | act {_money(v.actual)} | "
                f"delta {_money(v.delta)} | {pct_s}"
            )
        lines.append("")
    if r.unestimated_services:
        lines.append("UNESTIMATED SPEND (in actuals, no estimate provided):")
        for s in r.unestimated_services:
            lines.append(f"  ! {s}")
        lines.append("")
    if not r.anomalies and not r.unestimated_services:
        lines.append("No anomalies. Estimated billing matches actual within tolerance.")
        lines.append("")
    return "\n".join(lines)


def _idle_text(r: IdleReport) -> str:
    lines = [
        "IDLE / OVER-PROVISIONED RESOURCES",
        f"  Monthly cost reviewed : {_money(r.total_cost)}",
        f"  Potential savings     : {_money(r.total_savings)} ({len(r.findings)} findings)",
        "",
    ]
    if not r.findings:
        lines.append("No idle / over-provisioned resources detected.")
        lines.append("")
        return "\n".join(lines)
    by_sev = {"CRITICAL": [], "WARN": [], "INFO": []}
    for f in r.findings:
        by_sev.setdefault(f.severity, []).append(f)
    for sev in ("CRITICAL", "WARN", "INFO"):
        group = by_sev.get(sev) or []
        if not group:
            continue
        lines.append(f"{sev} ({len(group)}):")
        for f in group:
            lines.append(
                f"  {f.resource_id} ({f.rtype}) {_money(f.monthly_cost)}/mo -> "
                f"save {_money(f.estimated_savings)} : {f.reason}"
            )
        lines.append("")
    return "\n".join(lines)
