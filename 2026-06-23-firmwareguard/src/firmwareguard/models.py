"""Data models for FirmwareGuard."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class VulnStatus(str, Enum):
    ACTIVE = "active"
    PATCHED = "patched"
    UNPATCHABLE = "unpatchable"
    MITIGATED = "mitigated"


class DeviceStatus(str, Enum):
    COMPLIANT = "compliant"
    AT_RISK = "at_risk"
    NON_COMPLIANT = "non_compliant"
    UNKNOWN = "unknown"


@dataclass
class FirmwareVulnerability:
    vid: str
    title: str
    description: str
    severity: Severity
    vendor: str
    affected_products: list[str]
    cve_ids: list[str] = field(default_factory=list)
    status: VulnStatus = VulnStatus.ACTIVE
    discovered_date: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    patched_date: Optional[datetime] = None
    mitigation: Optional[str] = None
    references: list[str] = field(default_factory=list)

    @property
    def is_unpatchable(self) -> bool:
        return self.status == VulnStatus.UNPATCHABLE

    @property
    def age_days(self) -> int:
        delta = datetime.now(timezone.utc) - self.discovered_date
        return delta.days


@dataclass
class Device:
    device_id: str
    name: str
    vendor: str
    model: str
    firmware_version: str
    firmware_date: Optional[datetime] = None
    status: DeviceStatus = DeviceStatus.UNKNOWN
    last_scan: Optional[datetime] = None
    matched_vulns: list[str] = field(default_factory=list)

    def update_status(self, vulns: list[FirmwareVulnerability]) -> None:
        """Recompute device status based on matched vulnerabilities."""
        self.last_scan = datetime.now(timezone.utc)
        if not vulns:
            self.status = DeviceStatus.COMPLIANT
            return
        severities = [v.severity for v in vulns]
        if Severity.CRITICAL in severities:
            self.status = DeviceStatus.NON_COMPLIANT
        elif Severity.HIGH in severities:
            self.status = DeviceStatus.AT_RISK
        else:
            self.status = DeviceStatus.AT_RISK


@dataclass
class Fleet:
    fleet_id: str
    name: str
    devices: list[Device] = field(default_factory=list)

    @property
    def device_count(self) -> int:
        return len(self.devices)

    @property
    def risk_summary(self) -> dict[str, int]:
        summary = {}
        for d in self.devices:
            key = d.status.value
            summary[key] = summary.get(key, 0) + 1
        return summary

    def devices_by_status(self, status: DeviceStatus) -> list[Device]:
        return [d for d in self.devices if d.status == status]
