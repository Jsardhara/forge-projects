"""Fleet scanner — matches devices against known vulnerabilities."""

from datetime import datetime, timezone
from firmwareguard.models import (
    Device,
    DeviceStatus,
    Fleet,
    FirmwareVulnerability,
    Severity,
)
from firmwareguard.vulndb import KNOWN_VULNS


def match_device(device: Device) -> list[FirmwareVulnerability]:
    """Match a device against known vulnerabilities by vendor/model."""
    matched = []
    device_full = f"{device.vendor} {device.model}".lower()
    device_vendor = device.vendor.lower()
    for vuln in KNOWN_VULNS:
        vuln_vendor = vuln.vendor.lower()
        # Vendor must match first (skip "multiple" vendor — match all)
        if vuln_vendor != "multiple" and vuln_vendor not in device_full:
            continue
        # Then check if any affected product matches
        for product in vuln.affected_products:
            product_lower = product.lower()
            # Direct substring match
            if product_lower in device_full or device_full in product_lower:
                matched.append(vuln)
                break
            # Token-based match: check if key tokens from product appear in device
            # e.g., "Intel Core 6th-10th Gen" → check "Intel Core" + generation number
            product_tokens = set(product_lower.replace("-", " ").split())
            device_tokens = set(device_full.replace("-", " ").split())
            # Check for shared meaningful tokens (longer than 2 chars)
            shared = {t for t in product_tokens & device_tokens if len(t) > 2}
            if len(shared) >= 2:
                matched.append(vuln)
                break
    return matched


def scan_device(device: Device) -> Device:
    """Scan a single device and update its status."""
    vulns = match_device(device)
    device.matched_vulns = [v.vid for v in vulns]
    device.update_status(vulns)
    return device


def scan_fleet(fleet: Fleet) -> Fleet:
    """Scan all devices in a fleet."""
    for device in fleet.devices:
        scan_device(device)
    return fleet


def fleet_risk_score(fleet: Fleet) -> float:
    """Calculate a 0-100 risk score for the fleet.

    Score is weighted by severity:
    - CRITICAL: 25 points per device
    - HIGH: 15 points per device
    - MEDIUM: 5 points per device
    - LOW: 1 point per device

    Capped at 100.
    """
    if not fleet.devices:
        return 0.0

    score = 0.0
    for device in fleet.devices:
        vulns = match_device(device)
        for v in vulns:
            if v.severity == Severity.CRITICAL:
                score += 25.0
            elif v.severity == Severity.HIGH:
                score += 15.0
            elif v.severity == Severity.MEDIUM:
                score += 5.0
            elif v.severity == Severity.LOW:
                score += 1.0

    # Normalize by device count to avoid fleet-size bias
    score = score / len(fleet.devices)
    return min(score, 100.0)


def compliance_report(fleet: Fleet) -> dict:
    """Generate a compliance report for the fleet."""
    scan_fleet(fleet)
    summary = fleet.risk_summary

    total = fleet.device_count
    compliant = summary.get(DeviceStatus.COMPLIANT.value, 0)
    at_risk = summary.get(DeviceStatus.AT_RISK.value, 0)
    non_compliant = summary.get(DeviceStatus.NON_COMPLIANT.value, 0)

    findings = []
    for device in fleet.devices:
        if device.status == DeviceStatus.NON_COMPLIANT:
            vulns = match_device(device)
            critical_vulns = [v for v in vulns if v.severity == Severity.CRITICAL]
            for v in critical_vulns:
                findings.append(
                    f"[BLOCKING] {device.device_id} ({device.name}): "
                    f"{v.vid} — {v.title}"
                )

    return {
        "fleet_id": fleet.fleet_id,
        "fleet_name": fleet.name,
        "scan_time": datetime.now(timezone.utc).isoformat(),
        "total_devices": total,
        "compliant": compliant,
        "at_risk": at_risk,
        "non_compliant": non_compliant,
        "compliance_rate": (compliant / total * 100) if total > 0 else 100.0,
        "risk_score": fleet_risk_score(fleet),
        "findings": findings,
    }
