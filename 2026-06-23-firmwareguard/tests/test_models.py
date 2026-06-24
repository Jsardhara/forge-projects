"""Tests for FirmwareGuard models."""

from datetime import datetime, timedelta, timezone

from firmwareguard.models import (
    Device,
    DeviceStatus,
    Fleet,
    FirmwareVulnerability,
    Severity,
    VulnStatus,
)


class TestFirmwareVulnerability:
    def test_create_basic(self):
        v = FirmwareVulnerability(
            vid="TEST-001",
            title="Test Vuln",
            description="A test vulnerability",
            severity=Severity.HIGH,
            vendor="TestVendor",
            affected_products=["TestDevice"],
        )
        assert v.vid == "TEST-001"
        assert v.severity == Severity.HIGH
        assert v.status == VulnStatus.ACTIVE

    def test_is_unpatchable_true(self):
        v = FirmwareVulnerability(
            vid="TEST-002",
            title="Unpatchable",
            description="Cannot be patched",
            severity=Severity.CRITICAL,
            vendor="TestVendor",
            affected_products=["TestDevice"],
            status=VulnStatus.UNPATCHABLE,
        )
        assert v.is_unpatchable is True

    def test_is_unpatchable_false(self):
        v = FirmwareVulnerability(
            vid="TEST-003",
            title="Patchable",
            description="Can be patched",
            severity=Severity.HIGH,
            vendor="TestVendor",
            affected_products=["TestDevice"],
            status=VulnStatus.ACTIVE,
        )
        assert v.is_unpatchable is False

    def test_age_days(self):
        old_date = datetime.now(timezone.utc) - timedelta(days=30)
        v = FirmwareVulnerability(
            vid="TEST-004",
            title="Old Vuln",
            description="Discovered 30 days ago",
            severity=Severity.MEDIUM,
            vendor="TestVendor",
            affected_products=["TestDevice"],
            discovered_date=old_date,
        )
        assert v.age_days == 30

    def test_default_discovered_date_is_utc(self):
        v = FirmwareVulnerability(
            vid="TEST-005",
            title="Default Date",
            description="Test",
            severity=Severity.LOW,
            vendor="TestVendor",
            affected_products=["TestDevice"],
        )
        assert v.discovered_date.tzinfo is not None


class TestDevice:
    def test_create_basic(self):
        d = Device(
            device_id="DEV-001",
            name="Test Device",
            vendor="Apple",
            model="iPhone 11",
            firmware_version="17.5.1",
        )
        assert d.device_id == "DEV-001"
        assert d.status == DeviceStatus.UNKNOWN
        assert d.matched_vulns == []

    def test_update_status_compliant(self):
        d = Device(
            device_id="DEV-002",
            name="Clean Device",
            vendor="Unknown",
            model="UnknownDevice",
            firmware_version="1.0",
        )
        d.update_status([])
        assert d.status == DeviceStatus.COMPLIANT

    def test_update_status_non_compliant(self):
        v = FirmwareVulnerability(
            vid="TEST-006",
            title="Critical Vuln",
            description="Critical",
            severity=Severity.CRITICAL,
            vendor="TestVendor",
            affected_products=["TestDevice"],
        )
        d = Device(
            device_id="DEV-003",
            name="At Risk Device",
            vendor="TestVendor",
            model="TestDevice",
            firmware_version="1.0",
        )
        d.update_status([v])
        assert d.status == DeviceStatus.NON_COMPLIANT

    def test_update_status_at_risk(self):
        v = FirmwareVulnerability(
            vid="TEST-007",
            title="High Vuln",
            description="High severity",
            severity=Severity.HIGH,
            vendor="TestVendor",
            affected_products=["TestDevice"],
        )
        d = Device(
            device_id="DEV-004",
            name="Medium Risk Device",
            vendor="TestVendor",
            model="TestDevice",
            firmware_version="1.0",
        )
        d.update_status([v])
        assert d.status == DeviceStatus.AT_RISK

    def test_update_status_sets_last_scan(self):
        d = Device(
            device_id="DEV-005",
            name="Test",
            vendor="Unknown",
            model="Unknown",
            firmware_version="1.0",
        )
        assert d.last_scan is None
        d.update_status([])
        assert d.last_scan is not None


class TestFleet:
    def test_create_empty(self):
        f = Fleet(fleet_id="F-001", name="Empty Fleet")
        assert f.device_count == 0
        assert f.risk_summary == {}

    def test_device_count(self):
        f = Fleet(
            fleet_id="F-002",
            name="Test Fleet",
            devices=[
                Device(device_id="D1", name="Dev1", vendor="A", model="M1", firmware_version="1.0"),
                Device(device_id="D2", name="Dev2", vendor="B", model="M2", firmware_version="2.0"),
                Device(device_id="D3", name="Dev3", vendor="C", model="M3", firmware_version="3.0"),
            ],
        )
        assert f.device_count == 3

    def test_risk_summary(self):
        d1 = Device(device_id="D1", name="Dev1", vendor="A", model="M1", firmware_version="1.0", status=DeviceStatus.COMPLIANT)
        d2 = Device(device_id="D2", name="Dev2", vendor="B", model="M2", firmware_version="2.0", status=DeviceStatus.AT_RISK)
        d3 = Device(device_id="D3", name="Dev3", vendor="C", model="M3", firmware_version="3.0", status=DeviceStatus.NON_COMPLIANT)
        f = Fleet(fleet_id="F-003", name="Summary Fleet", devices=[d1, d2, d3])
        summary = f.risk_summary
        assert summary["compliant"] == 1
        assert summary["at_risk"] == 1
        assert summary["non_compliant"] == 1

    def test_devices_by_status(self):
        d1 = Device(device_id="D1", name="Dev1", vendor="A", model="M1", firmware_version="1.0", status=DeviceStatus.COMPLIANT)
        d2 = Device(device_id="D2", name="Dev2", vendor="B", model="M2", firmware_version="2.0", status=DeviceStatus.COMPLIANT)
        d3 = Device(device_id="D3", name="Dev3", vendor="C", model="M3", firmware_version="3.0", status=DeviceStatus.AT_RISK)
        f = Fleet(fleet_id="F-004", name="Filter Fleet", devices=[d1, d2, d3])
        compliant = f.devices_by_status(DeviceStatus.COMPLIANT)
        assert len(compliant) == 2
        assert all(d.status == DeviceStatus.COMPLIANT for d in compliant)
