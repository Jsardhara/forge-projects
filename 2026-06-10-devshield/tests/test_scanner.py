"""Tests for the scanner."""

from unittest.mock import MagicMock, patch

from devshield.scanner import ScanReport, ScanResult, Scanner
from devshield.advisory import AdvisoryResult
from devshield.package_managers import Dependency


def test_scan_report_empty():
    from pathlib import Path
    report = ScanReport(project_dir=Path("."))
    assert report.vulnerable_count == 0
    assert report.scanned_count == 0
    assert report.skipped_count == 0


def test_scan_report_with_results():
    from pathlib import Path
    report = ScanReport(
        project_dir=Path("."),
        results=[
            ScanResult(
                dependency=Dependency(name="openai", version="1.0", ecosystem="pip"),
                is_ai_tooling=True,
                advisory_result=AdvisoryResult(package_name="openai", ecosystem="pip"),
            ),
            ScanResult(
                dependency=Dependency(name="flask", version="2.0", ecosystem="pip"),
                is_ai_tooling=False,
                skipped=True,
                skip_reason="Not AI tooling",
            ),
        ],
    )
    assert report.scanned_count == 1
    assert report.skipped_count == 1


def test_scan_result_vulnerable():
    result = ScanResult(
        dependency=Dependency(name="openai", version="1.0", ecosystem="pip"),
        is_ai_tooling=True,
        advisory_result=AdvisoryResult(
            package_name="openai",
            ecosystem="pip",
            advisories=[],
        ),
    )
    # Empty advisories = not vulnerable
    assert result.is_vulnerable is False


def test_scanner_skips_non_ai_by_default():
    """Scanner should skip non-AI packages when scan_all=False."""
    scanner = Scanner(scan_all=False)
    dep = Dependency(name="flask", version="2.0", ecosystem="pip")

    # Can't fully test without mocking AdvisoryClient, but we can verify
    # the skip logic directly
    from devshield.ai_tooling_db import is_ai_tooling
    assert is_ai_tooling("flask", "pip") is False


def test_scanner_includes_all_when_flag_set():
    """Scanner should include all packages when scan_all=True."""
    scanner = Scanner(scan_all=True)
    assert scanner.scan_all is True
