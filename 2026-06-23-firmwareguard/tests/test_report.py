"""Tests for FirmwareGuard report formatter."""

from firmwareguard.models import Device, DeviceStatus, Fleet
from firmwareguard.report import (
    format_device_detail,
    format_json,
    format_report,
    format_vuln_detail,
)
from firmwareguard.scanner import compliance_report
from firmwareguard.vulndb import get_vuln_by_id


class TestFormatReport:
    def test_text_output_contains_fleet_name(self):
        f = Fleet(
            fleet_id="F1",
            name="Test Fleet",
            devices=[
                Device(device_id="D1", name="Dev1", vendor="Unknown", model="Unknown", firmware_version="1.0"),
            ],
        )
        report = compliance_report(f)
        text = format_report(report)
        assert "Test Fleet" in text

    def test_text_output_contains_compliance_rate(self):
        f = Fleet(
            fleet_id="F2",
            name="Rate Fleet",
            devices=[
                Device(device_id="D1", name="Dev1", vendor="Unknown", model="Unknown", firmware_version="1.0"),
            ],
        )
        report = compliance_report(f)
        text = format_report(report)
        assert "Compliance Rate" in text

    def test_text_output_contains_risk_score(self):
        f = Fleet(
            fleet_id="F3",
            name="Score Fleet",
            devices=[
                Device(device_id="D1", name="Dev1", vendor="Unknown", model="Unknown", firmware_version="1.0"),
            ],
        )
        report = compliance_report(f)
        text = format_report(report)
        assert "Risk Score" in text


class TestFormatDeviceDetail:
    def test_contains_device_id(self):
        d = Device(
            device_id="DEV-001",
            name="Test Device",
            vendor="Unknown",
            model="Unknown",
            firmware_version="1.0",
        )
        text = format_device_detail(d)
        assert "DEV-001" in text

    def test_contains_status(self):
        d = Device(
            device_id="DEV-002",
            name="Test Device",
            vendor="Unknown",
            model="Unknown",
            firmware_version="1.0",
            status=DeviceStatus.COMPLIANT,
        )
        text = format_device_detail(d)
        assert "compliant" in text

    def test_matched_vulns_shown(self):
        d = Device(
            device_id="DEV-003",
            name="iPhone",
            vendor="Apple",
            model="iPhone 11 Pro",
            firmware_version="17.5.1",
        )
        text = format_device_detail(d)
        assert "FG-001" in text


class TestFormatVulnDetail:
    def test_contains_vid(self):
        v = get_vuln_by_id("FG-001")
        text = format_vuln_detail(v)
        assert "FG-001" in text

    def test_contains_severity(self):
        v = get_vuln_by_id("FG-001")
        text = format_vuln_detail(v)
        assert "CRITICAL" in text

    def test_contains_mitigation(self):
        v = get_vuln_by_id("FG-001")
        text = format_vuln_detail(v)
        assert "Device replacement" in text

    def test_unpatchable_flagged(self):
        v = get_vuln_by_id("FG-001")
        text = format_vuln_detail(v)
        assert "unpatchable" in text.lower() or "UNPATCHABLE" in text


class TestFormatJson:
    def test_valid_json(self):
        import json
        f = Fleet(
            fleet_id="F4",
            name="JSON Fleet",
            devices=[
                Device(device_id="D1", name="Dev1", vendor="Unknown", model="Unknown", firmware_version="1.0"),
            ],
        )
        report = compliance_report(f)
        text = format_json(report)
        parsed = json.loads(text)
        assert parsed["fleet_id"] == "F4"
