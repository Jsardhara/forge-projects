"""Assemble and render the attestation.

Two rules are structural, not stylistic:

1. The verdict line always carries the exit code, so a reader who ignores the
   code still sees whether "nothing at threshold" was actually established.
2. Every probe branch prints how many targets were probed and how many came
   back. A table that shows no findings in a branch it never read is
   indistinguishable from a clean one.
"""

import json

from . import bulletins
from .collect import ABSENT, MEASURED, UNREADABLE

STATUS_LABEL = {
    bulletins.OPEN: "OPEN",
    bulletins.CLOSED: "CLOSED",
    bulletins.NOT_APPLICABLE: "NOT APPLICABLE",
    bulletins.UNKNOWN: "UNKNOWN",
}


def _counts(results):
    out = {bulletins.OPEN: 0, bulletins.CLOSED: 0,
           bulletins.NOT_APPLICABLE: 0, bulletins.UNKNOWN: 0}
    for item in results:
        out[item.status] = out.get(item.status, 0) + 1
    return out


def build_report(collected):
    """Turn a Collected into a plain dict (JSON-ready)."""
    results = bulletins.evaluate(collected.facts)
    name = bulletins.verdict(results)
    counts = _counts(results)
    mitigation = collected.mitigation
    return {
        "tool": "tsattest",
        "node": collected.node,
        "version": collected.version_raw,
        "backend_state": collected.backend_state,
        "verdict": name,
        "exit_code": bulletins.exit_code(name),
        "bulletins": [r.as_dict() for r in results],
        "bulletin_counts": {
            "probed": len(results),
            "open": counts.get(bulletins.OPEN, 0),
            "closed": counts.get(bulletins.CLOSED, 0),
            "not_applicable": counts.get(bulletins.NOT_APPLICABLE, 0),
            "unknown": counts.get(bulletins.UNKNOWN, 0),
        },
        "ssh": {
            "enabled": collected.facts.ssh_enabled,
            "source": collected.ssh_source,
            "status_host_keys_present": collected.ssh_host_keys_present,
        },
        "serve": {
            "present": collected.facts.serve_present,
            "unix_backend": collected.facts.serve_unix_backend,
        },
        "mitigation": mitigation.as_dict(),
        "probes": {
            "probed": collected.probe_count(),
            "measured": collected.measured_count(),
            "unmeasurable": collected.unmeasurable_count(),
            "items": [p.as_dict() for p in collected.probes],
        },
        "notes": list(collected.notes or ()),
    }


def _fmt_ssh(report):
    enabled = report["ssh"]["enabled"]
    state = {True: "enabled", False: "disabled", None: "UNKNOWN"}[enabled]
    line = "ssh: %s (decision source: %s)" % (state, report["ssh"]["source"])
    keys = report["ssh"]["status_host_keys_present"]
    if keys is False:
        line += "\n     status --json Self.SSH_HostKeys = null   [not used]"
    return line


def _fmt_mitigation(report):
    mit = report["mitigation"]
    declared = mit["declared"]
    actual = mit["actual"]
    declared_text = ("%r" % declared["value"] if declared["status"] == MEASURED
                     else "%s -- %s" % (declared["status"].upper(),
                                        declared.get("reason") or "no reason"))
    actual_text = ("%r" % actual["value"] if actual["status"] == MEASURED
                   else "%s -- %s" % (actual["status"].upper(),
                                      actual.get("reason") or "no reason"))
    return "\n".join([
        "mitigation TS_SSH_DISABLE_FORWARDING",
        "  declared (%s): %s" % (declared["source"], declared_text),
        "  actual   (%s): %s" % (actual["source"], actual_text),
        "  consistency: %s" % mit["consistency"],
        "  advice: %s" % mit["advice"],
    ])


def _fmt_bulletins(report):
    counts = report["bulletin_counts"]
    lines = ["bulletins: %d probed, %d open, %d closed, %d not applicable, %d unknown"
             % (counts["probed"], counts["open"], counts["closed"],
                counts["not_applicable"], counts["unknown"])]
    for item in report["bulletins"]:
        lines.append("  [%-14s] %s  fixed in %s" % (STATUS_LABEL[item["status"]],
                                                   item["key"], item["fixed_in"]))
        lines.append("  %16s %s" % ("", item["detail"]))
    return "\n".join(lines)


def _fmt_probes(report):
    probes = report["probes"]
    lines = ["probes: %d probed, %d measured, %d unmeasurable"
             % (probes["probed"], probes["measured"], probes["unmeasurable"]),
             "probe coverage: %d of %d" % (probes["measured"], probes["probed"])]
    for item in probes["items"]:
        status = item["status"]
        label = {MEASURED: "measured", UNREADABLE: "UNREADABLE",
                 ABSENT: "absent"}.get(status, status)
        suffix = " -- %s" % item["reason"] if item.get("reason") else ""
        lines.append("  - %-9s %-11s %s%s" % (item["name"], label, item["source"], suffix))
    return "\n".join(lines)


def render_plain(report):
    lines = [
        "tsattest -- is this client's Tailscale SSH mitigation actually loaded?",
        "node: %s   version: %s   backend: %s"
        % (report["node"], report["version"] or "UNKNOWN",
           report["backend_state"] or "UNKNOWN"),
        "verdict: %s (exit %d)" % (report["verdict"], report["exit_code"]),
        "",
        _fmt_ssh(report),
        "",
        _fmt_bulletins(report),
        "",
        _fmt_mitigation(report),
        "",
        _fmt_probes(report),
    ]
    for note in report["notes"]:
        lines.append("")
        lines.append("note: %s" % note)
    return "\n".join(lines)


def render_json(report):
    return json.dumps(report, indent=2, sort_keys=True)
