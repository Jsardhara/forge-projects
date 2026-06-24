"""Tests for FirmwareGuard vulnerability database."""

from firmwareguard.models import Severity, VulnStatus
from firmwareguard.vulndb import (
    KNOWN_VULNS,
    get_active,
    get_unpatchable,
    get_vuln_by_id,
    get_vulns_by_severity,
    get_vulns_by_vendor,
)


class TestKnownVulns:
    def test_database_not_empty(self):
        assert len(KNOWN_VULNS) > 0

    def test_all_have_ids(self):
        for v in KNOWN_VULNS:
            assert v.vid.startswith("FG-")

    def test_all_have_severity(self):
        for v in KNOWN_VULNS:
            assert isinstance(v.severity, Severity)

    def test_all_have_vendor(self):
        for v in KNOWN_VULNS:
            assert len(v.vendor) > 0

    def test_all_have_affected_products(self):
        for v in KNOWN_VULNS:
            assert len(v.affected_products) > 0

    def test_unique_ids(self):
        ids = [v.vid for v in KNOWN_VULNS]
        assert len(ids) == len(set(ids))


class TestGetVulnById:
    def test_find_existing(self):
        v = get_vuln_by_id("FG-001")
        assert v is not None
        assert v.vid == "FG-001"

    def test_not_found(self):
        assert get_vuln_by_id("FG-999") is None

    def test_case_sensitive(self):
        # Should not find lowercase
        assert get_vuln_by_id("fg-001") is None


class TestGetVulnsByVendor:
    def test_apple(self):
        vulns = get_vulns_by_vendor("Apple")
        assert len(vulns) > 0
        assert all(v.vendor == "Apple" for v in vulns)

    def test_intel(self):
        vulns = get_vulns_by_vendor("Intel")
        assert len(vulns) > 0

    def test_unknown_vendor(self):
        assert get_vulns_by_vendor("NonExistentCorp") == []

    def test_case_insensitive(self):
        vulns_lower = get_vulns_by_vendor("apple")
        vulns_upper = get_vulns_by_vendor("Apple")
        assert len(vulns_lower) == len(vulns_upper)


class TestGetVulnsBySeverity:
    def test_critical(self):
        vulns = get_vulns_by_severity(Severity.CRITICAL)
        assert all(v.severity == Severity.CRITICAL for v in vulns)

    def test_high_includes_critical(self):
        vulns = get_vulns_by_severity(Severity.HIGH)
        severities = {v.severity for v in vulns}
        assert Severity.CRITICAL in severities
        assert Severity.HIGH in severities

    def test_low_includes_all(self):
        vulns = get_vulns_by_severity(Severity.LOW)
        assert len(vulns) == len(KNOWN_VULNS)


class TestGetUnpatchable:
    def test_returns_unpatchable_only(self):
        vulns = get_unpatchable()
        assert all(v.status == VulnStatus.UNPATCHABLE for v in vulns)

    def test_apple_bootrom_included(self):
        vulns = get_unpatchable()
        ids = [v.vid for v in vulns]
        assert "FG-001" in ids


class TestGetActive:
    def test_returns_active_only(self):
        vulns = get_active()
        assert all(v.status == VulnStatus.ACTIVE for v in vulns)

    def test_excludes_patched(self):
        vulns = get_active()
        ids = [v.vid for v in vulns]
        # FG-003 (Qualcomm) is PATCHED
        assert "FG-003" not in ids
