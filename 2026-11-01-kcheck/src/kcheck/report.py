"""Render the answer. Two audiences: a human at 3am, and a cron/jq consumer.

The text output names, in this order: the running kernel, the fixed target, the gap, the
demonstrated-path measurement, the tracker URL with its retrieval date, and the
mitigation pointer. It never states or implies exposure it did not measure -- the
exposure line prints the scopes that were actually found and the prefixes they matched.

One renderer, driven by the same dict that ``--json`` emits. Two renderers would drift,
and the human view is the one nobody writes tests against.
"""

from .assess import FIXED, NOT_AFFECTED, UNKNOWN, VULNERABLE, exit_code as _exit_code

EXIT_MEANING = {
    0: "clean -- the installed kernel is not in range of any checked CVE",
    1: "findings -- the installed kernel is in range, or the attack path is reachable",
    2: "unmeasurable -- no verified fix row for this distro, or a probe could not be read",
}

VERDICT_LABEL = {
    VULNERABLE: "VULNERABLE",
    FIXED: "FIXED",
    NOT_AFFECTED: "NOT AFFECTED",
    UNKNOWN: "UNMEASURABLE",
}

_VERDICT_NAME = {0: "CLEAN", 1: "FINDINGS", 2: "UNMEASURABLE"}

_STATE_LABEL = {"pending": "fix_pending", "released": "fix_released",
                "not_affected": "not_affected"}

_STATE_SUFFIX = {
    "pending": " -- NOT RELEASED (vendor: fix in progress)",
    "released": " -- released",
    "not_affected": " -- vendor marks this release as not affected",
}


def build_report(findings, facts, table_doc, now):
    findings = tuple(findings)
    code = _exit_code(findings)
    return {
        "tool": "kcheck",
        "now": now,
        "exit_code": code,
        "verdict": _VERDICT_NAME[code],
        "verdict_meaning": EXIT_MEANING[code],
        "host": {
            "running_release": facts.release,
            "installed_package": facts.package_name,
            "installed_version": facts.package_version,
            "kernel_images": list(facts.kernel_images),
            "distro": facts.distro,
            "distro_release": facts.distro_release,
            "distro_codename": facts.distro_codename,
            "mptcp_enabled": facts.mptcp_enabled,
            "mptcp_listener_count": (len(facts.mptcp_listeners)
                                     if facts.mptcp_listeners is not None else None),
            "mptcp_listeners": [
                {"address": l.address, "port": l.port, "scope": l.scope, "network": l.network}
                for l in (facts.mptcp_listeners or ())
            ],
            "exposure_surface": list(facts.exposure_surface),
            "probe_errors": list(facts.errors),
        },
        "table": {
            "path": table_doc.path,
            "generated_at": table_doc.generated_at,
            "stale_after_days": table_doc.stale_after_days,
            "cves_loaded": len(table_doc.cves),
        },
        "findings": [_finding_row(f) for f in findings],
        "notes": [
            "read-only, offline, no root, no third-party dependencies",
            "the fix table is checked in and dated; a stale row is reported, never hidden",
            "mitigation is a pointer for the operator, never applied by this tool",
        ],
    }


def _finding_row(finding):
    return {
        "cve": finding.cve,
        "title": finding.title,
        "cvss": finding.cvss,
        "cvss_vector": finding.vector,
        "verdict": finding.verdict,
        "in_range": finding.in_range,
        "on_demonstrated_path": finding.on_demonstrated_path,
        "fix_state": finding.fix_state,
        "installed_version": finding.installed_version,
        "installed_package": finding.installed_package,
        "running_release": finding.running_release,
        "fixed_version": finding.fixed_version,
        "abi_gap": finding.abi_gap,
        "exposure_surface": list(finding.exposure_surface),
        "mptcp_enabled": finding.mptcp_enabled,
        "mptcp_listener_count": finding.listener_count,
        "attack_path": {"label": finding.attack_path_label, "probe": finding.attack_probe},
        "mitigation": finding.mitigation,
        "source_url": finding.source_url,
        "retrieved_at": finding.retrieved_at,
        "provenance_age_days": finding.provenance_age_days,
        "provenance_stale": finding.provenance_stale,
        "reason": finding.reason,
    }


# --- text ---------------------------------------------------------------------------

def _distro_text(host):
    parts = [host["distro"] or "unknown"]
    if host["distro_release"]:
        parts.append(host["distro_release"])
    if host["distro_codename"]:
        parts.append("(%s)" % host["distro_codename"])
    return " ".join(parts)


def _host_lines(host):
    surface = ", ".join(host["exposure_surface"]) or "none"
    networks = sorted({listener["network"] for listener in host["mptcp_listeners"]})
    enabled = host["mptcp_enabled"]
    if enabled is None:
        mptcp = "unreadable (sysctl net.mptcp.enabled did not return a value)"
    else:
        mptcp = "net.mptcp.enabled = %d (%s)" % (enabled, "enabled" if enabled else "disabled")
    if host["mptcp_listener_count"] is None:
        listeners = "unreadable (ss -Mln gave no table)"
    else:
        listeners = "%d listener(s)" % host["mptcp_listener_count"]
    image = ("%s %s" % (host["installed_package"], host["installed_version"])
             if host["installed_package"] else "not found in the package DB")
    return [
        "  %-17s %s" % ("running kernel", host["running_release"] or "unreadable"),
        "  %-17s %s" % ("installed image", image),
        "  %-17s %s" % ("distro", _distro_text(host)),
        "  %-17s %s" % ("mptcp", mptcp),
        "  %-17s %s" % ("mptcp listeners", listeners),
        "  %-17s %s%s" % ("exposure", surface,
                          (" (%s)" % ", ".join(networks)) if networks else ""),
    ]


def _fixed_line(row):
    if row["verdict"] == UNKNOWN:
        return "unknown -- %s" % row["reason"]
    fixed = row["fixed_version"] or "unknown"
    return fixed + _STATE_SUFFIX.get(row["fix_state"], "")


def _gap_line(row):
    if row["verdict"] == UNKNOWN:
        return "not computed -- the comparison could not be made"
    if row["abi_gap"] is None:
        return "not comparable (different upstream train)"
    if row["abi_gap"] <= 0:
        return "none -- at or past the fixed ABI"
    return "%d ABI levels behind (%s -> %s)" % (
        row["abi_gap"], _abi(row["installed_version"]), _abi(row["fixed_version"]))


def _path_line(row):
    label = row["attack_path"]["label"]
    probe = row["attack_path"]["probe"]
    if row["on_demonstrated_path"] is True:
        return "ON PATH -- %s (probe: %s); %d listener(s)" % (
            label, probe, row["mptcp_listener_count"])
    if row["on_demonstrated_path"] is False:
        return "not on path -- %s (probe: %s); no reachable listener" % (label, probe)
    return "UNMEASURED -- %s (probe: %s could not be read)" % (label, probe)


def _provenance_line(row):
    if row["retrieved_at"] is None:
        return "none -- no verified row for this distro"
    age = row["provenance_age_days"]
    text = "unknown age" if age is None else "%d days old" % age
    return text + (" -- STALE, re-verify against the tracker" if row["provenance_stale"] else "")


def _abi(version):
    from . import dpkgver
    if not version:
        return "?"
    try:
        return str(dpkgver.abi(version))
    except dpkgver.VersionError:
        return "?"


def _finding_lines(row):
    header = "%s  %s" % (row["cve"], VERDICT_LABEL[row["verdict"]])
    if row["fix_state"]:
        header += "  %s" % _STATE_LABEL.get(row["fix_state"], row["fix_state"])
    header += "  CVSS %.1f" % row["cvss"]
    tracker = row["source_url"] or "no verified row"
    if row["retrieved_at"]:
        tracker += " (retrieved %s)" % row["retrieved_at"]
    return [
        header,
        "  %s" % row["title"],
        "  %-17s %s (package %s)" % ("running", row["running_release"] or "unreadable",
                                     row["installed_version"] or "unreadable"),
        "  %-17s %s" % ("fixed target", _fixed_line(row)),
        "  %-17s %s" % ("gap", _gap_line(row)),
        "  %-17s %s" % ("attack path", _path_line(row)),
        "  %-17s %s" % ("exposure", ", ".join(row["exposure_surface"]) or "no listeners"),
        "  %-17s %s" % ("tracker", tracker),
        "  %-17s %s" % ("provenance", _provenance_line(row)),
    ]


def _mitigation_lines(findings):
    if not findings:
        return []
    lines = ["", "MITIGATION -- not applied by kcheck; this is an operator decision (T3/T4)"]
    for row in findings:
        lines.append("  %s: %s" % (row["cve"], row["mitigation"].get("summary", "")))
        lines.append("  pointer: %s" % row["mitigation"]["pointer"])
    lines.append("  kcheck prints this pointer only. It never runs nft/iptables and never writes")
    lines.append("  a sysctl -- a firewall rule fired by a checker is an outage waiting to happen.")
    lines.append("  The real fix is the vendor kernel.")
    return lines


def render_text(report):
    lines = ["kcheck -- is THIS host's kernel in a known CVE's range?  (%s)" % report["now"],
             "", "HOST (measured, not inferred)"]
    lines.extend(_host_lines(report["host"]))
    for row in report["findings"]:
        lines.append("")
        lines.extend(_finding_lines(row))
    if report["exit_code"] != 0:
        # A clean run does not need a mitigation lecture: there is nothing to mitigate.
        lines.extend(_mitigation_lines([r for r in report["findings"] if r["mitigation"]]))
    lines.append("")
    lines.append("exit: %d -- %s" % (report["exit_code"], report["verdict_meaning"]))
    return "\n".join(lines) + "\n"
