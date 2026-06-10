"""Tests for the advisory client."""

from unittest.mock import MagicMock, patch

import pytest

from devshield.advisory import Advisory, AdvisoryClient, AdvisoryResult


def test_advisory_result_no_vulnerabilities():
    result = AdvisoryResult(package_name="openai", ecosystem="pip")
    assert result.is_vulnerable is False
    assert result.max_severity == "none"


def test_advisory_result_with_vulnerabilities():
    adv = Advisory(
        ghsa_id="GHSA-test-1234",
        cve_id="CVE-2026-0001",
        summary="Test vulnerability",
        description="A test vuln",
        severity="high",
        url="https://github.com/advisories/GHSA-test-1234",
    )
    result = AdvisoryResult(
        package_name="openai",
        ecosystem="pip",
        advisories=[adv],
    )
    assert result.is_vulnerable is True
    assert result.max_severity == "high"


def test_advisory_result_max_severity_critical():
    advs = [
        Advisory(ghsa_id="GHSA-1", cve_id=None, summary="Low", description="", severity="low", url=""),
        Advisory(ghsa_id="GHSA-2", cve_id=None, summary="Critical", description="", severity="critical", url=""),
    ]
    result = AdvisoryResult(package_name="test", ecosystem="npm", advisories=advs)
    assert result.max_severity == "critical"


def test_advisory_result_error():
    result = AdvisoryResult(package_name="test", ecosystem="npm", error="Connection failed")
    assert result.error == "Connection failed"
    assert result.is_vulnerable is False


def test_parse_advisory():
    data = {
        "ghsa_id": "GHSA-abc-123",
        "summary": "Test advisory",
        "description": "A test advisory",
        "severity": "high",
        "html_url": "https://github.com/advisories/GHSA-abc-123",
        "identifiers": [{"type": "CVE", "value": "CVE-2026-1234"}],
        "vulnerabilities": [
            {"package": {"name": "openai", "ecosystem": "pip"}}
        ],
    }

    adv = AdvisoryClient._parse_advisory(data)
    assert adv.ghsa_id == "GHSA-abc-123"
    assert adv.cve_id == "CVE-2026-1234"
    assert adv.severity == "high"
    assert "pip/openai" in adv.affected_packages


def test_parse_advisory_no_cve():
    data = {
        "ghsa_id": "GHSA-xyz",
        "summary": "No CVE",
        "description": "",
        "severity": "medium",
        "html_url": "",
        "identifiers": [{"type": "GHSA", "value": "GHSA-xyz"}],
        "vulnerabilities": [],
    }

    adv = AdvisoryClient._parse_advisory(data)
    assert adv.cve_id is None
    assert adv.severity == "medium"
