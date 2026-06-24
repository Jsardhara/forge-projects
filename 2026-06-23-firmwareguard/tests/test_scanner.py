"""Tests for FirmwareGuard scanner."""

from datetime import datetime, timezone

from firmwareguard.models import Device, DeviceStatus, Fleet, FirmwareVulnerability, Severity
from firmwareguard.scanner import (
    compliance_report,
    fleet_risk_score,
    match_device,
    scan_device,
    scan_fleet,
)


class TestMatchDevice:
    def test_apple_device_matches_bootrom(self):
        d = Device(
            device_id="D1",
            name="iPhone",
            vendor="Apple",
            model="iPhone 11 Pro",
            firmware_version="17.5.1",
        )
        vulns = match_device(d)
        ids = [v.vid for v in vulns]
        assert "FG-001" in ids  # Apple BootROM

    def test_intel_device_matches_me(self):
        d = Device(
            device_id="D2",
            name="Laptop",
            vendor="Intel",
            model="Intel Core i7-10700K",
            firmware_version="14.2",
        )
        vulns = match_device(d)
        ids = [v.vid for v in vulns]
        assert "FG-002" in ids  # Intel ME

    def test_unknown_device_no_match(self):
        d = Device(
            device_id="D3",
            name="Unknown",
            vendor="UnknownVendor",
            model="UnknownModel",
            firmware_version="1.0",
        )
        vulns = match_device(d)
        assert len(vulns) == 0

    def test_qualcomm_device_matches_baseband(self):
        d = Device(
            device_id="D4",
            name="Android Phone",
            vendor="Qualcomm",
            model="Snapdragon 888",
            firmware_version="V1.0",
        )
        vulns = match_device(d)
        ids = [v.vid for v in vulns]
        assert "FG-003" in ids  # Qualcomm baseband


class TestScanDevice:
    def test_scan_updates_status(self):
        d = Device(
            device_id="D5",
            name="Test",
            vendor="Apple",
            model="iPhone 11 Pro",
            firmware_version="17.5.1",
        )
        result = scan_device(d)
        assert result.status in (DeviceStatus.NON_COMPLIANT, DeviceStatus.AT_RISK)

    def test_scan_sets_matched_vulns(self):
        d = Device(
            device_id="D6",
            name="Test",
            vendor="Apple",
            model="iPhone 11 Pro",
            firmware_version="17.5.1",
        )
        scan_device(d)
        assert len(d.matched_vulns) > 0

    def test_scan_sets_last_scan(self):
        d = Device(
            device_id="D7",
            name="Test",
            vendor="Unknown",
            model="Unknown",
            firmware_version="1.0",
        )
        scan_device(d)
        assert d.last_scan is not None

    def test_clean_device_compliant(self):
        d = Device(
            device_id="D8",
            name="Clean",
            vendor="UnknownVendor",
            model="UnknownModel",
            firmware_version="1.0",
        )
        scan_device(d)
        assert d.status == DeviceStatus.COMPLIANT


class TestScanFleet:
    def test_scan_all_devices(self):
        f = Fleet(
            fleet_id="F1",
            name="Test Fleet",
            devices=[
                Device(device_id="D1", name="Dev1", vendor="Apple", model="iPhone 11 Pro", firmware_version="17.5.1"),
                Device(device_id="D2", name="Dev2", vendor="Unknown", model="Unknown", firmware_version="1.0"),
            ],
        )
        scan_fleet(f)
        assert all(d.last_scan is not None for d in f.devices)


class TestFleetRiskScore:
    def test_empty_fleet_zero(self):
        f = Fleet(fleet_id="F2", name="Empty")
        assert fleet_risk_score(f) == 0.0

    def test_clean_fleet_zero(self):
        f = Fleet(
            fleet_id="F3",
            name="Clean Fleet",
            devices=[
                Device(device_id="D1", name="Dev1", vendor="Unknown", model="Unknown", firmware_version="1.0"),
            ],
        )
        assert fleet_risk_score(f) == 0.0

    def test_at_risk_fleet_positive(self):
        f = Fleet(
            fleet_id="F4",
            name="Risky Fleet",
            devices=[
                Device(device_id="D1", name="Dev1", vendor="Apple", model="iPhone 11 Pro", firmware_version="17.5.1"),
            ],
        )
        score = fleet_risk_score(f)
        assert score > 0.0

    def test_score_capped_at_100(self):
        # Many critical devices should still cap at 100
        devices = [
            Device(device_id=f"D{i}", name=f"Dev{i}", vendor="Apple", model="iPhone 11 Pro", firmware_version="17.5.1")
            for i in range(20)
        ]
        f = Fleet(fleet_id="F5", name="Large Risky Fleet", devices=devices)
        score = fleet_risk_score(f)
        assert score <= 100.0


class TestComplianceReport:
    def test_report_has_required_keys(self):
        f = Fleet(
            fleet_id="F6",
            name="Report Fleet",
            devices=[
                Device(device_id="D1", name="Dev1", vendor="Apple", model="iPhone 11 Pro", firmware_version="17.5.1"),
            ],
        )
        report = compliance_report(f)
        assert "fleet_id" in report
        assert "fleet_name" in report
        assert "scan_time" in report
        assert "total_devices" in report
        assert "compliant" in report
        assert "at_risk" in report
        assert "non_compliant" in report
        assert "compliance_rate" in report
        assert "risk_score" in report
        assert "findings" in report

    def test_report_counts(self):
        f = Fleet(
            fleet_id="F7",
            name="Count Fleet",
            devices=[
                Device(device_id="D1", name="Dev1", vendor="Apple", model="iPhone 11 Pro", firmware_version="17.5.1"),
                Device(device_id="D2", name="Dev2", vendor="Unknown", model="Unknown", firmware_version="1.0"),
            ],
        )
        report = compliance_report(f)
        assert report["total_devices"] == 2

    def test_report_finding_for_critical(self):
        f = Fleet(
            fleet_id="F8",
            name="Critical Fleet",
            devices=[
                Device(device_id="D1", name="Dev1", vendor="Apple", model="iPhone 11 Pro", firmware_version="17.5.1"),
            ],
        )
        report = compliance_report(f)
        # Apple BootROM is CRITICAL, should produce a blocking finding
        assert len(report["findings"]) > 0

    def test_compliance_rate_range(self):
        f = Fleet(
            fleet_id="F9",
            name="Rate Fleet",
            devices=[
                Device(device_id="D1", name="Dev1", vendor="Unknown", model="Unknown", firmware_version="1.0"),
            ],
        )
        report = compliance_report(f)
        assert 0.0 <= report["compliance_rate"] <= 100.0
