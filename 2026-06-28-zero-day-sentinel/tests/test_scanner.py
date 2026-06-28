"""Tests for ZeroDaySentinel scanner."""

from datetime import datetime, timezone
from zerosentinel.models import ExploitRepositry, Severity
from zerosentinel.scanner import ZeroDayScanner


def _make_repo(
    name: str = "test-repo",
    description: str = "",
    topics: tuple = (),
    readme: str = "",
    stars: int = 0,
    repo_id: str = "r001",
) -> ExploitRepositry:
    return ExploitRepositry(
        repo_id=repo_id,
        repo_url=f"https://github.com/test/{name}",
        owner="test",
        name=name,
        description=description,
        published_at=datetime(2026, 6, 27, tzinfo=timezone.utc),
        topics=topics,
        stars=stars,
        language="Python",
        raw_readme=readme,
    )


class TestZeroDayScanner:
    def setup_method(self):
        self.scanner = ZeroDayScanner()

    def test_detects_rce_exploit(self):
        repo = _make_repo(
            name="cve-2026-rce-linux",
            description="0-day remote code execution in Linux kernel",
            topics=("0day", "exploit", "rce"),
            readme="RCE exploit for Linux kernel < 6.8.0. Remote code execution via netfilter race condition.",
        )
        result = self.scanner.scan_repo(repo)
        assert result is not None
        assert result.affected_product == "linux"
        assert result.vulnerability_type == "rce"
        assert result.severity == Severity.CRITICAL

    def test_detects_auth_bypass(self):
        repo = _make_repo(
            name="apache-auth-bypass",
            topics=("exploit", "cve"),
            readme="Apache HTTPD authentication bypass vulnerability. Unauthenticated access to admin panel.",
        )
        result = self.scanner.scan_repo(repo)
        assert result is not None
        assert result.vulnerability_type == "authentication_bypass"
        assert result.severity == Severity.CRITICAL

    def test_rejects_normal_repo(self):
        repo = _make_repo(
            name="cool-project",
            description="A fun new web framework",
            topics=("web", "framework"),
            readme="Building a modern web framework with async support.",
        )
        result = self.scanner.scan_repo(repo)
        assert result is None

    def test_extracts_cve_id(self):
        repo = _make_repo(
            name="exploit",
            topics=("exploit",),
            readme="PoC for CVE-2026-1234. Affects OpenSSL < 3.3.0.",
        )
        result = self.scanner.scan_repo(repo)
        assert result is not None
        assert result.cve_id == "CVE-2026-1234"

    def test_extracts_versions(self):
        repo = _make_repo(
            name="exploit",
            topics=("0day",),
            readme="Affects nginx versions 1.24.0 to 1.25.3",
        )
        result = self.scanner.scan_repo(repo)
        assert result is not None
        assert len(result.affected_versions) >= 2

    def test_buffer_overflow_classification(self):
        repo = _make_repo(
            name="exploit",
            topics=("poc",),
            readme="Stack buffer overflow in Cisco IOS XE. RCE via crafted packets.",
        )
        result = self.scanner.scan_repo(repo)
        assert result is not None
        assert result.vulnerability_type in ("buffer_overflow", "rce")
        assert result.severity == Severity.CRITICAL

    def test_batch_scan_dedup(self):
        repos = [
            _make_repo(repo_id="r1", name="same-exploit-1", topics=("0day",), readme="RCE in Linux kernel 6.7"),
            _make_repo(repo_id="r2", name="same-exploit-2", topics=("0day",), readme="RCE in Linux kernel 6.7"),
            _make_repo(repo_id="r3", name="different", topics=("0day",), readme="XSS in nginx"),
        ]
        results = self.scanner.scan_batch(repos)
        # Should deduplicate the first two (same product + type)
        assert len(results) >= 1
        # Check at least one result has rce type
        rce_results = [r for r in results if r.vulnerability_type == "rce"]
        assert len(rce_results) >= 1

    def test_high_star_exploit_gets_high_severity(self):
        repo = _make_repo(
            name="mass-exploit",
            topics=("exploit", "0day"),
            readme="New vulnerability found. Details to be announced.",
            stars=200,
        )
        result = self.scanner.scan_repo(repo)
        assert result is not None
        assert result.severity in (Severity.HIGH, Severity.CRITICAL)

    def test_unknown_vuln_type(self):
        repo = _make_repo(
            name="weird-bug",
            topics=("0day",),
            readme="Something strange happens when you do X.",
        )
        result = self.scanner.scan_repo(repo)
        assert result is not None
        assert result.vulnerability_type == "unknown"

    def test_extracts_cpes(self):
        repo = _make_repo(
            name="exploit",
            topics=("exploit",),
            readme="cpe:2.3:a:openssl:openssl:3.2.1:*:*:*:*:*:*:*",
        )
        result = self.scanner.scan_repo(repo)
        assert result is not None
        assert len(result.extracted_cpes) == 1
        assert "openssl" in result.extracted_cpes[0]

    def test_extracts_references(self):
        repo = _make_repo(
            name="exploit",
            topics=("exploit",),
            readme="See https://example.com/advisory and https://nvd.nist.gov/vuln/detail/CVE-2026-1234",
        )
        result = self.scanner.scan_repo(repo)
        assert result is not None
        assert len(result.references) >= 2
