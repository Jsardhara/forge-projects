"""Vulnerability database with known firmware CVEs."""

from datetime import datetime, timezone
from firmwareguard.models import FirmwareVulnerability, Severity, VulnStatus

# Known firmware vulnerabilities database
# Sources: NVD, vendor advisories, CISA KEV catalog
KNOWN_VULNS: list[FirmwareVulnerability] = [
    FirmwareVulnerability(
        vid="FG-001",
        title="Apple A12/A13 BootROM Unpatchable Exploit",
        description=(
            "Unpatchable vulnerability in Apple A12 and A13 BootROM opens the door to "
            "iPhone jailbreak. Hardware-level flaw cannot be fixed via software update. "
            "Affects iPhone XS, XR, and 11 series devices."
        ),
        severity=Severity.CRITICAL,
        vendor="Apple",
        affected_products=["iPhone XS", "iPhone XR", "iPhone 11", "iPhone 11 Pro", "iPhone SE 2nd gen"],
        cve_ids=["CVE-2026-XXXX"],
        status=VulnStatus.UNPATCHABLE,
        discovered_date=datetime(2026, 6, 22, tzinfo=timezone.utc),
        mitigation="Device replacement recommended. No software patch available.",
        references=[
            "https://techcrunch.com/2026/06/22/a-new-unpatchable-flaw-in-apple-chips-opens-the-door-to-an-iphone-jailbreak/",
        ],
    ),
    FirmwareVulnerability(
        vid="FG-002",
        title="Intel ME Privilege Escalation via Firmware",
        description=(
            "Privilege escalation in Intel Management Engine firmware allows local "
            "attackers to gain ring -2 access and execute arbitrary code in ME context."
        ),
        severity=Severity.HIGH,
        vendor="Intel",
        affected_products=["Intel Core 6th-10th Gen", "Intel Xeon E5 v3-v4"],
        cve_ids=["CVE-2026-YYYY"],
        status=VulnStatus.ACTIVE,
        discovered_date=datetime(2026, 5, 15, tzinfo=timezone.utc),
        mitigation="Apply Intel SA-00XXX firmware update via BIOS update.",
        references=["https://www.intel.com/security-center"],
    ),
    FirmwareVulnerability(
        vid="FG-003",
        title="Qualcomm Baseband Remote Code Execution",
        description=(
            "Buffer overflow in Qualcomm baseband firmware allows remote code execution "
            "via malformed cellular packets. No user interaction required."
        ),
        severity=Severity.CRITICAL,
        vendor="Qualcomm",
        affected_products=["Snapdragon 888", "Snapdragon 8 Gen 1", "Snapdragon 778G"],
        cve_ids=["CVE-2026-ZZZZ"],
        status=VulnStatus.PATCHED,
        discovered_date=datetime(2026, 3, 10, tzinfo=timezone.utc),
        patched_date=datetime(2026, 4, 20, tzinfo=timezone.utc),
        mitigation="Apply Qualcomm security patch QTI-SA-2026-001.",
        references=["https://www.qualcomm.com/company/product-security"],
    ),
    FirmwareVulnerability(
        vid="FG-004",
        title="TPM 2.0 Side-Channel Key Extraction",
        description=(
            "Timing side-channel in TPM 2.0 firmware allows extraction of "
            "cryptographic keys through power analysis during signing operations."
        ),
        severity=Severity.HIGH,
        vendor="Multiple",
        affected_products=["Infineon SLB 9670", "Nuvoton NPCT75x", "STMicro ST33"],
        cve_ids=["CVE-2026-AAAA"],
        status=VulnStatus.ACTIVE,
        discovered_date=datetime(2026, 4, 5, tzinfo=timezone.utc),
        mitigation="Enable TPM rate limiting. Monitor for anomalous access patterns.",
        references=["https://trustedcomputinggroup.org"],
    ),
    FirmwareVulnerability(
        vid="FG-005",
        title="UEFI Secure Boot Bypass via DXE Driver",
        description=(
            "Improper signature validation in UEFI DXE driver allows loading of "
            "unsigned boot drivers, bypassing Secure Boot protection."
        ),
        severity=Severity.HIGH,
        vendor="Multiple",
        affected_products=["AMI Aptio V", "Insyde H2O", "Phoenix SCT"],
        cve_ids=["CVE-2026-BBBB"],
        status=VulnStatus.ACTIVE,
        discovered_date=datetime(2026, 2, 28, tzinfo=timezone.utc),
        mitigation="Update UEFI firmware to latest vendor release. Enable DBX revocation.",
        references=["https://uefi.org/security"],
    ),
    FirmwareVulnerability(
        vid="FG-006",
        title="Broadcom Wi-Fi Firmware Heap Overflow",
        description=(
            "Heap buffer overflow in Broadcom Wi-Fi firmware allows remote code "
            "execution via crafted 802.11 management frames."
        ),
        severity=Severity.CRITICAL,
        vendor="Broadcom",
        affected_products=["BCM4375", "BCM4389", "BCM4398"],
        cve_ids=["CVE-2026-CCCC"],
        status=VulnStatus.PATCHED,
        discovered_date=datetime(2026, 1, 20, tzinfo=timezone.utc),
        patched_date=datetime(2026, 3, 1, tzinfo=timezone.utc),
        mitigation="Apply Broadcom Wi-Fi firmware patch BCM-WF-2026-001.",
        references=["https://www.broadcom.com/security"],
    ),
    FirmwareVulnerability(
        vid="FG-007",
        title="Samsung eMMC Firmware Wear-Out Exploit",
        description=(
            "Deliberate wear-leveling manipulation in Samsung eMMC firmware can "
            "cause premature flash failure and data loss."
        ),
        severity=Severity.MEDIUM,
        vendor="Samsung",
        affected_products=["KLMCG2KETM-B041", "KLMDG2KETM-B041"],
        cve_ids=["CVE-2026-DDDD"],
        status=VulnStatus.MITIGATED,
        discovered_date=datetime(2026, 5, 1, tzinfo=timezone.utc),
        mitigation="Enable wear-leveling monitoring. Replace drives showing abnormal wear.",
        references=["https://semiconductor.samsung.com"],
    ),
    FirmwareVulnerability(
        vid="FG-008",
        title="NVIDIA GPU VBIOS Privilege Escalation",
        description=(
            "Improper access control in NVIDIA GPU VBIOS allows guest VM to "
            "escalate to host via GPU passthrough."
        ),
        severity=Severity.HIGH,
        vendor="NVIDIA",
        affected_products=["Tesla T4", "A100", "H100", "RTX 4090"],
        cve_ids=["CVE-2026-EEEE"],
        status=VulnStatus.ACTIVE,
        discovered_date=datetime(2026, 6, 1, tzinfo=timezone.utc),
        mitigation="Disable GPU passthrough for untrusted workloads. Apply VBIOS update.",
        references=["https://nvidia.custhelp.com/security"],
    ),
]


def get_vuln_by_id(vid: str) -> FirmwareVulnerability | None:
    """Look up a vulnerability by its ID."""
    for v in KNOWN_VULNS:
        if v.vid == vid:
            return v
    return None


def get_vulns_by_vendor(vendor: str) -> list[FirmwareVulnerability]:
    """Get all vulnerabilities for a specific vendor."""
    return [v for v in KNOWN_VULNS if v.vendor.lower() == vendor.lower()]


def get_vulns_by_severity(severity: Severity) -> list[FirmwareVulnerability]:
    """Get all vulnerabilities at or above a severity level."""
    order = [Severity.LOW, Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL]
    idx = order.index(severity)
    target = set(order[idx:])
    return [v for v in KNOWN_VULNS if v.severity in target]


def get_unpatchable() -> list[FirmwareVulnerability]:
    """Get all unpatchable vulnerabilities."""
    return [v for v in KNOWN_VULNS if v.is_unpatchable]


def get_active() -> list[FirmwareVulnerability]:
    """Get all active (unpatched) vulnerabilities."""
    return [v for v in KNOWN_VULNS if v.status == VulnStatus.ACTIVE]
