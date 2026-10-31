"""Render the exit contract. Two audiences: a human at 3am, and a cron/jq consumer."""
from .models import DEGRADED, HALTED, UNMEASURABLE

EXIT_MEANING = {
    0: "clean -- every measured exit path is open",
    1: "findings -- at least one exit path is degraded or halted",
    2: "unmeasurable -- nothing contradicted, but a required signal could not be read",
}


def verdict(venues, chains) -> int:
    """1 outranks 2: a real halt must never be hidden behind 'could not measure'.

    A venue declared `uncovered` (no public status signal exists) is coverage debt, not a
    measurement failure -- it is printed and counted, but it cannot pin the exit code at 2
    forever, or the gate is noise and gets ignored.
    """
    blocked = any(v.state in (DEGRADED, HALTED) for v in venues) or any(not c.ok for c in chains)
    if blocked:
        return 1
    unmeasured = [v for v in venues if v.state == UNMEASURABLE and v.kind != "uncovered"]
    if unmeasured:
        return 2
    return 0


def _venue_row(v) -> dict:
    return {
        "slug": v.slug,
        "name": v.name,
        "kind": v.kind,
        "state": v.state,
        "reason": v.reason,
        "http_code": v.http_code,
        "confidence": v.confidence,
        "paused_networks": list(v.paused_networks),
        "degraded_networks": list(v.degraded_networks),
        "source_url": v.source_url,
        "observed_at": v.observed_at,
        "components_checked": v.checked,
        "page_status": v.page_status,
        "signals": [{"component": s.component, "state": s.state, "note": s.note} for s in v.signals],
    }


def build_report(venues, chains, now: str) -> dict:
    venues, chains = tuple(venues), tuple(chains)
    code = verdict(venues, chains)
    measured = [v for v in venues if v.measurable]
    return {
        "tool": "exitpath",
        "now": now,
        "exit_code": code,
        "verdict": EXIT_MEANING[code],
        "coverage": {
            "venues_total": len(venues),
            "venues_measured": len(measured),
            "venues_unmeasurable": len(venues) - len(measured),
            "chains_total": len(chains),
            "chains_healthy": sum(1 for c in chains if c.ok),
        },
        "venues": [_venue_row(v) for v in venues],
        "chains": [
            {"chain": c.chain, "endpoint": c.endpoint, "ok": c.ok,
             "block_height": c.block_height, "latency_ms": c.latency_ms, "error": c.error}
            for c in chains
        ],
    }


def _venue_line(row: dict) -> str:
    non_open = [s for s in row["signals"] if s["state"] in ("degraded", "halted")]
    if row["state"] == UNMEASURABLE:
        detail = "unmeasurable: %s" % (row["reason"] or "unknown reason")
    elif non_open or row["paused_networks"] or row["degraded_networks"]:
        parts = []
        if row["paused_networks"]:
            parts.append("paused on %s" % ", ".join(row["paused_networks"]))
        elif row["degraded_networks"]:
            parts.append("degraded on %s" % ", ".join(row["degraded_networks"]))
        shown = non_open[:3]
        if shown:
            extra = len(non_open) - len(shown)
            bits = ["%s %s" % (s["component"], s["state"]) for s in shown]
            parts.append("; ".join(bits) + (" (+%d more)" % extra if extra else ""))
        detail = " | ".join(parts)
    else:
        detail = "%d exit components checked, all open" % row["components_checked"]
        if row.get("page_status"):
            # The venue-wide indicator can be degraded while the exit slice reads open --
            # say so, otherwise a real problem elsewhere on the page looks like a clean bill.
            detail += " | venue page: %s" % row["page_status"]
    return "  %-10s %-13s %s" % (row["slug"], row["state"], detail)


def _chain_line(row: dict) -> str:
    if row["ok"]:
        where = ("block %d" % row["block_height"]) if row["block_height"] is not None else "healthy"
        return "  %-10s healthy   %s (%sms)" % (row["chain"], where, row["latency_ms"])
    return "  %-10s UNSAFE    %s" % (row["chain"], row["error"])


def render_text(report: dict) -> str:
    lines = ["exitpath -- can funds actually leave?  (%s)" % report["now"], ""]
    lines.append("VENUES / ISSUERS")
    lines.extend(_venue_line(v) for v in report["venues"])
    lines.append("")
    lines.append("CHAINS (a 200 is not health; a block height is)")
    lines.extend(_chain_line(c) for c in report["chains"])
    cov = report["coverage"]
    lines.append("")
    lines.append(
        "coverage: venues %d/%d measured, chains %d/%d healthy"
        % (cov["venues_measured"], cov["venues_total"], cov["chains_healthy"], cov["chains_total"])
    )
    lines.append("exit: %d -- %s" % (report["exit_code"], report["verdict"]))
    return "\n".join(lines) + "\n"
