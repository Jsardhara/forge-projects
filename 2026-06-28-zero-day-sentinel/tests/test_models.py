"""Tests for ZeroDaySentinel models."""

from datetime import datetime, timezone
from zerosentinel.models import (
    DetectionResult,
    ExploitRepositry,
    PatchSuggestion,
    Severity,
    VulnerabilityFingerprint,
)


class TestExploitRepositry:
    def test_from_dict_basic(self):
        repo = ExploitRepositry.from_dict({
            "repo_id": "r001",
            "repo_url": "https://github.com/test/repo",
            "owner": "test",
            "name": "exploit-repo",
            "description": "A test exploit",
            "published_at": "2026-06-27T14:30:00Z",
            "topics": ("exploit", "cve"),
            "stars": 100,
            "language": "Python",
        })
        assert repo.repo_id == "r001"
        assert repo.owner == "test"
        assert repo.stars == 100
        assert repo.topics == ("exploit", "cve")

    def test_from_dict_no_date(self):
        repo = ExploitRepositry.from_dict({
            "repo_id": "r002",
            "repo_url": "https://github.com/a/b",
            "owner": "a",
            "name": "b",
            "description": "",
            "published_at": None,
            "topics": (),
            "stars": 0,
            "language": "",
        })
        assert repo.published_at is not None
        assert repo.published_at.tzinfo == timezone.utc

    def test_from_dict_empty(self):
        repo = ExploitRepositry.from_dict({})
        assert repo.repo_id == ""
        assert repo.owner == ""


class TestVulnerabilityFingerprint:
    def test_is_critical_true(self):
        fp = VulnerabilityFingerprint(
            cve_id="CVE-2026-0001",
            affected_product="linux",
            affected_versions=("6.8.0",),
            vulnerability_type="rce",
            severity=Severity.CRITICAL,
            summary="test",
        )
        assert fp.is_critical is True

    def test_is_critical_false(self):
        fp = VulnerabilityFingerprint(
            cve_id=None,
            affected_product="nginx",
            affected_versions=("1.25",),
            vulnerability_type="xss",
            severity=Severity.MEDIUM,
            summary="test",
        )
        assert fp.is_critical is False

    def test_fingerprint_key(self):
        fp = VulnerabilityFingerprint(
            cve_id="CVE-2026-0001",
            affected_product="linux",
            affected_versions=(),
            vulnerability_type="rce",
            severity=Severity.CRITICAL,
            summary="",
        )
        assert fp.fingerprint_key == "linux:rce:CVE-2026-0001"

    def test_fingerprint_key_no_cve(self):
        fp = VulnerabilityFingerprint(
            cve_id=None,
            affected_product="openssl",
            affected_versions=(),
            vulnerability_type="buffer_overflow",
            severity=Severity.HIGH,
            summary="",
        )
        assert fp.fingerprint_key == "openssl:buffer_overflow:unknown"


class TestPatchSuggestion:
    def test_is_high_confidence(self):
        ps = PatchSuggestion(
            fingerprint=VulnerabilityFingerprint(
                cve_id=None,
                affected_product="linux",
                affected_versions=(),
                vulnerability_type="rce",
                severity=Severity.CRITICAL,
                summary="",
            ),
            confidence=0.85,
            suggested_fix="Update linux kernel",
            patch_type="version_pin",
        )
        assert ps.is_high_confidence is True

    def test_is_not_high_confidence(self):
        ps = PatchSuggestion(
            fingerprint=VulnerabilityFingerprint(
                cve_id=None,
                affected_product="linux",
                affected_versions=(),
                vulnerability_type="rce",
                severity=Severity.LOW,
                summary="",
            ),
            confidence=0.3,
            suggested_fix="Update linux kernel",
            patch_type="version_pin",
        )
        assert ps.is_high_confidence is False


class TestDetectionResult:
    def test_has_matches_empty(self):
        result = DetectionResult(
            scan_timestamp=datetime.now(timezone.utc),
            repos_scanned=0,
            matches=(),
            patch_suggestions=(),
            scan_duration_seconds=0.1,
        )
        assert result.has_matches is False
        assert result.critical_count == 0

    def test_has_matches_with_data(self):
        fp = VulnerabilityFingerprint(
            cve_id="CVE-2026-0001",
            affected_product="linux",
            affected_versions=("6.8.0",),
            vulnerability_type="rce",
            severity=Severity.CRITICAL,
            summary="test critical",
        )
        result = DetectionResult(
            scan_timestamp=datetime.now(timezone.utc),
            repos_scanned=5,
            matches=(fp,),
            patch_suggestions=(),
            scan_duration_seconds=0.5,
        )
        assert result.has_matches is True
        assert result.critical_count == 1

    def test_multiple_severities(self):
        fps = [
            VulnerabilityFingerprint(
                cve_id=None, affected_product=p, affected_versions=(),
                vulnerability_type="rce", severity=s, summary="",
            )
            for p, s in [
                ("linux", Severity.CRITICAL),
                ("openssl", Severity.HIGH),
                ("nginx", Severity.CRITICAL),
            ]
        ]
        result = DetectionResult(
            scan_timestamp=datetime.now(timezone.utc),
            repos_scanned=3,
            matches=tuple(fps),
            patch_suggestions=(),
            scan_duration_seconds=0.1,
        )
        assert result.critical_count == 2
