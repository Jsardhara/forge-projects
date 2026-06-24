"""Report generator — formatted output for fleet compliance reports."""

from firmwareguard.models import Device, DeviceStatus, Fleet, Severity
from firmwareguard.scanner import compliance_report, fleet_risk_score, match_device


def format_report(report: dict) -> str:
    """Format a compliance report as human-readable text."""
    lines = []
    lines.append("=" * 60)
    lines.append(f"  FirmwareGuard Compliance Report")
    lines.append(f"  Fleet: {report['fleet_name']}")
    lines.append(f"  Scan Time: {report['scan_time']}")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"  Total Devices:    {report['total_devices']}")
    lines.append(f"  Compliant:       {report['compliant']}")
    lines.append(f"  At Risk:         {report['at_risk']}")
    lines.append(f"  Non-Compliant:   {report['non_compliant']}")
    lines.append(f"  Compliance Rate: {report['compliance_rate']:.1f}%")
    lines.append(f"  Risk Score:      {report['risk_score']:.1f}/100")
    lines.append("")

    if report["findings"]:
        lines.append("-" * 60)
        lines.append("  BLOCKING FINDINGS:")
        lines.append("-" * 60)
        for f in report["findings"]:
            lines.append(f"  {f}")
        lines.append("")

    lines.append("=" * 60)
    return "\n".join(lines)


def format_device_detail(device: Device) -> str:
    """Format detailed device information."""
    vulns = match_device(device)
    lines = []
    lines.append(f"Device: {device.device_id} — {device.name}")
    lines.append(f"  Vendor: {device.vendor}")
    lines.append(f"  Model: {device.model}")
    lines.append(f"  Firmware: {device.firmware_version}")
    lines.append(f"  Status: {device.status.value}")
    lines.append(f"  Last Scan: {device.last_scan or 'Never'}")
    if vulns:
        lines.append(f"  Matched Vulnerabilities ({len(vulns)}):")
        for v in vulns:
            lines.append(f"    [{v.severity.value.upper():8s}] {v.vid}: {v.title}")
            if v.is_unpatchable:
                lines.append(f"              *** UNPATCHABLE — {v.mitigation or 'No mitigation available'}")
    else:
        lines.append("  No known vulnerabilities matched.")
    return "\n".join(lines)


def format_vuln_detail(vuln) -> str:
    """Format detailed vulnerability information."""
    lines = []
    lines.append(f"Vulnerability: {vuln.vid}")
    lines.append(f"  Title: {vuln.title}")
    lines.append(f"  Severity: {vuln.severity.value.upper()}")
    lines.append(f"  Vendor: {vuln.vendor}")
    lines.append(f"  Status: {vuln.status.value}")
    lines.append(f"  Discovered: {vuln.discovered_date.isoformat()}")
    if vuln.patched_date:
        lines.append(f"  Patched: {vuln.patched_date.isoformat()}")
    lines.append(f"  Age: {vuln.age_days} days")
    lines.append(f"  Affected Products: {', '.join(vuln.affected_products)}")
    if vuln.cve_ids:
        lines.append(f"  CVE IDs: {', '.join(vuln.cve_ids)}")
    lines.append(f"  Description: {vuln.description}")
    if vuln.mitigation:
        lines.append(f"  Mitigation: {vuln.mitigation}")
    if vuln.references:
        lines.append(f"  References:")
        for ref in vuln.references:
            lines.append(f"    - {ref}")
    return "\n".join(lines)


def format_json(report: dict) -> str:
    """Format report as JSON."""
    import json
    return json.dumps(report, indent=2, default=str)
