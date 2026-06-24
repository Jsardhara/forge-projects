# FirmwareGuard — Firmware Vulnerability Tracker & Fleet Compliance

FirmwareGuard is a Python toolkit for tracking firmware vulnerabilities across device fleets. It correlates device firmware versions against known CVEs, generates compliance reports, and provides risk-prioritized remediation guidance.

## Why FirmwareGuard?

Hardware-level firmware vulnerabilities are surging:
- **June 2026**: Unpatchable BootROM exploit in Apple A12/A13 chips (hundreds of millions of iPhones)
- **May 2026**: Tata Electronics breach exposes Apple IP through supply-chain compromise
- **Ongoing**: Intel ME, Qualcomm baseband, TPM side-chains, UEFI Secure Boot bypasses

Enterprise IT teams have **zero tooling** to track firmware exposure across their device fleets. FirmwareGuard fills that gap.

## Features

- **Vulnerability Database**: 8 known firmware CVEs across Apple, Intel, Qualcomm, Broadcom, NVIDIA, Samsung, Infineon
- **Fleet Scanner**: Match devices against known vulnerabilities by vendor/model
- **Risk Scoring**: Weighted 0-100 risk score (CRITICAL=25, HIGH=15, MEDIUM=5, LOW=1)
- **Compliance Reports**: Text and JSON output with blocking findings
- **Unpatchable Detection**: Special handling for hardware-level flaws that can't be patched
- **Stdlib Only**: Zero external dependencies

## Installation

```bash
pip install firmwareguard
```

## Quick Start

```bash
# Show vulnerability database status
firmwareguard status

# Get details on a specific vulnerability
firmwareguard vuln FG-001

# Show all Apple vulnerabilities
firmwareguard vendor Apple

# Scan demo fleet
firmwareguard scan

# Scan with JSON output and device details
firmwareguard scan --format json --detail

# Scan a single device
firmwareguard device --name "My iPhone" --vendor Apple --model "iPhone 11 Pro" --firmware 17.5.1

# Show critical+ vulnerabilities
firmwareguard severity critical
```

## Python API

```python
from firmwareguard.models import Device, Fleet
from firmwareguard.scanner import compliance_report, scan_fleet
from firmwareguard.vulndb import get_vuln_by_id, get_unpatchable

# Create a fleet
fleet = Fleet(fleet_id="prod-001", name="Production Fleet", devices=[
    Device(device_id="D1", name="CEO Phone", vendor="Apple", model="iPhone 11 Pro", firmware_version="17.5.1"),
])

# Scan and get report
report = compliance_report(fleet)
print(f"Compliance Rate: {report['compliance_rate']:.1f}%")
print(f"Risk Score: {report['risk_score']:.1f}/100")

# Look up specific vulnerability
vuln = get_vuln_by_id("FG-001")
print(f"Unpatchable: {vuln.is_unpatchable}")
```

## Architecture

```
firmwareguard/
├── models.py      # Data models (Device, Fleet, FirmwareVulnerability)
├── vulndb.py      # Known vulnerability database + query functions
├── scanner.py     # Fleet scanning, matching, risk scoring
├── report.py      # Report formatting (text, JSON, detail views)
└── cli.py         # CLI interface
```

## License

MIT
