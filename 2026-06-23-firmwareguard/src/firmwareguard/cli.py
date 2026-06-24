"""CLI for FirmwareGuard."""

import argparse
import sys

from firmwareguard.models import Device, Fleet
from firmwareguard.vulndb import (
    KNOWN_VULNS,
    get_active,
    get_unpatchable,
    get_vuln_by_id,
    get_vulns_by_severity,
    get_vulns_by_vendor,
)
from firmwareguard.scanner import compliance_report, match_device, scan_device
from firmwareguard.report import (
    format_device_detail,
    format_json,
    format_report,
    format_vuln_detail,
)


def demo_fleet() -> Fleet:
    """Create a demo fleet for CLI testing."""
    return Fleet(
        fleet_id="demo-001",
        name="Enterprise Device Fleet",
        devices=[
            Device(
                device_id="DEV-001",
                name="CEO iPhone",
                vendor="Apple",
                model="iPhone 11 Pro",
                firmware_version="17.5.1",
            ),
            Device(
                device_id="DEV-002",
                name="Engineering Laptop",
                vendor="Intel",
                model="Intel Core i7-10700K",
                firmware_version="14.2.1",
            ),
            Device(
                device_id="DEV-003",
                name="Test Lab Phone",
                vendor="Qualcomm",
                model="Snapdragon 888",
                firmware_version="V1.2.3",
            ),
            Device(
                device_id="DEV-004",
                name="Dev Workstation",
                vendor="NVIDIA",
                model="RTX 4090",
                firmware_version="95.0.27",
            ),
            Device(
                device_id="DEV-005",
                name="Secure Server",
                vendor="Infineon",
                model="SLB 9670 TPM",
                firmware_version="7.8.2",
            ),
        ],
    )


def cmd_status(args):
    """Show vulnerability database status."""
    print(f"FirmwareGuard — Vulnerability Database Status")
    print(f"Total vulnerabilities: {len(KNOWN_VULNS)}")
    print(f"Active: {len(get_active())}")
    print(f"Unpatchable: {len(get_unpatchable())}")
    print()
    for vuln in KNOWN_VULNS:
        status_marker = "⚠️ " if vuln.is_unpatchable else "  "
        print(f"{status_marker}[{vuln.severity.value.upper():8s}] {vuln.vid}: {vuln.title} ({vuln.vendor})")


def cmd_vuln(args):
    """Show details for a specific vulnerability."""
    vuln = get_vuln_by_id(args.vuln_id.upper())
    if vuln is None:
        print(f"Error: Vulnerability '{args.vuln_id}' not found.", file=sys.stderr)
        sys.exit(1)
    print(format_vuln_detail(vuln))


def cmd_vendor(args):
    """Show vulnerabilities for a specific vendor."""
    vulns = get_vulns_by_vendor(args.vendor)
    if not vulns:
        print(f"No vulnerabilities found for vendor: {args.vendor}")
        return
    print(f"Vulnerabilities for {args.vendor}:")
    for v in vulns:
        print(f"  [{v.severity.value.upper():8s}] {v.vid}: {v.title}")


def cmd_scan(args):
    """Scan a demo fleet and show results."""
    fleet = demo_fleet()
    report = compliance_report(fleet)
    if args.format == "json":
        print(format_json(report))
    else:
        print(format_report(report))
        if args.detail:
            print("\nDevice Details:")
            print("-" * 60)
            for device in fleet.devices:
                print(format_device_detail(device))
                print()


def cmd_device(args):
    """Scan a single device."""
    device = Device(
        device_id="single",
        name=args.name,
        vendor=args.vendor,
        model=args.model,
        firmware_version=args.firmware,
    )
    scan_device(device)
    print(format_device_detail(device))


def cmd_severity(args):
    """Show vulnerabilities at or above a severity level."""
    severity_map = {
        "critical": Severity.CRITICAL,
        "high": Severity.HIGH,
        "medium": Severity.MEDIUM,
        "low": Severity.LOW,
    }
    sev = severity_map.get(args.level.lower())
    if sev is None:
        print(f"Error: Invalid severity '{args.level}'. Use: critical, high, medium, low", file=sys.stderr)
        sys.exit(1)
    vulns = get_vulns_by_severity(sev)
    print(f"Vulnerabilities at {args.level.upper()} or above ({len(vulns)}):")
    for v in vulns:
        print(f"  [{v.severity.value.upper():8s}] {v.vid}: {v.title} ({v.vendor})")


def main():
    parser = argparse.ArgumentParser(
        prog="firmwareguard",
        description="Firmware Vulnerability Tracker & Fleet Compliance",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # status
    subparsers.add_parser("status", help="Show vulnerability database status")

    # vuln
    vuln_p = subparsers.add_parser("vuln", help="Show vulnerability details")
    vuln_p.add_argument("vuln_id", help="Vulnerability ID (e.g., FG-001)")

    # vendor
    vendor_p = subparsers.add_parser("vendor", help="Show vendor vulnerabilities")
    vendor_p.add_argument("vendor", help="Vendor name (e.g., Apple)")

    # scan
    scan_p = subparsers.add_parser("scan", help="Scan demo fleet")
    scan_p.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    scan_p.add_argument("--detail", action="store_true", help="Show per-device details")

    # device
    dev_p = subparsers.add_parser("device", help="Scan a single device")
    dev_p.add_argument("--name", required=True, help="Device name")
    dev_p.add_argument("--vendor", required=True, help="Device vendor")
    dev_p.add_argument("--model", required=True, help="Device model")
    dev_p.add_argument("--firmware", default="unknown", help="Firmware version")

    # severity
    sev_p = subparsers.add_parser("severity", help="Filter by severity")
    sev_p.add_argument("level", choices=["critical", "high", "medium", "low"], help="Severity level")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return

    commands = {
        "status": cmd_status,
        "vuln": cmd_vuln,
        "vendor": cmd_vendor,
        "scan": cmd_scan,
        "device": cmd_device,
        "severity": cmd_severity,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
