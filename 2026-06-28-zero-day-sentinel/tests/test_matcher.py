"""Tests for ZeroDaySentinel dependency matcher."""

from zerosentinel.matcher import DependencyMatcher, _normalize_version, _version_matches_range
from zerosentinel.models import Severity, VulnerabilityFingerprint


def _make_fp(
    product: str = "linux",
    versions: tuple = (),
    vuln_type: str = "rce",
    severity: Severity = Severity.CRITICAL,
    cpes: tuple = (),
) -> VulnerabilityFingerprint:
    return VulnerabilityFingerprint(
        cve_id=None,
        affected_product=product,
        affected_versions=versions,
        vulnerability_type=vuln_type,
        severity=severity,
        summary="test",
        extracted_cpes=cpes,
    )


class TestVersionNormalization:
    def test_simple_version(self):
        assert _normalize_version("1.2.3") == (1, 2, 3)

    def test_two_part(self):
        assert _normalize_version("3.2") == (3, 2)

    def test_with_suffix(self):
        assert _normalize_version("1.2.3-beta") == (1, 2, 3, 0)

    def test_empty(self):
        assert _normalize_version("") == ()


class TestVersionMatching:
    def test_exact_match(self):
        assert _version_matches_range("1.2.3", ("1.2.3",)) is True

    def test_exact_mismatch(self):
        assert _version_matches_range("1.2.4", ("1.2.3",)) is False

    def test_prefix_wildcard(self):
        assert _version_matches_range("1.2.5", ("1.2.*",)) is True

    def test_prefix_mismatch(self):
        assert _version_matches_range("1.3.0", ("1.2.*",)) is False

    def test_range_match(self):
        assert _version_matches_range("1.5.0", ("1.0 - 2.0",)) is True

    def test_range_below(self):
        assert _version_matches_range("0.9.0", ("1.0 - 2.0",)) is False

    def test_range_above(self):
        assert _version_matches_range("2.1.0", ("1.0 - 2.0",)) is False

    def test_no_versions_matches_all(self):
        assert _version_matches_range("9.9.9", ()) is True


class TestDependencyMatcher:
    def setup_method(self):
        self.matcher = DependencyMatcher()

    def test_direct_match(self):
        fp = _make_fp(product="linux", versions=("6.7.0", "6.8.0"))
        assert self.matcher.is_vulnerable("linux", "6.7.0", fp) is True

    def test_direct_mismatch(self):
        fp = _make_fp(product="linux", versions=("6.7.0",))
        assert self.matcher.is_vulnerable("linux", "6.9.0", fp) is False

    def test_alias_match(self):
        fp = _make_fp(product="openssl", versions=("3.2.*",))
        assert self.matcher.is_vulnerable("libssl", "3.2.1", fp) is True

    def test_cpe_match(self):
        fp = _make_fp(product="linux", cpes=("cpe:2.3:o:linux:linux_kernel:6.7.0:*:*:*:*:*:*:*",))
        assert self.matcher.is_vulnerable("linux_kernel", "6.7.0", fp) is True

    def test_substring_match(self):
        fp = _make_fp(product="openssl")
        assert self.matcher.is_vulnerable("openssl3", "3.2.0", fp) is True

    def test_no_match_different_product(self):
        fp = _make_fp(product="linux")
        assert self.matcher.is_vulnerable("nginx", "1.25.0", fp) is False

    def test_find_vulnerable_dependencies(self):
        fp_linux = _make_fp(product="linux", versions=("6.7.0",))
        fp_nginx = _make_fp(product="nginx", versions=("1.25.*",))

        deps = {
            "linux": "6.7.0",
            "nginx": "1.25.3",
            "redis": "7.2.4",
        }
        results = self.matcher.find_vulnerable_dependencies(deps, [fp_linux, fp_nginx])
        assert len(results) == 2
        pkg_names = {r[0] for r in results}
        assert pkg_names == {"linux", "nginx"}

    def test_find_no_vulnerabilities(self):
        fp = _make_fp(product="windows")
        deps = {"linux": "6.7.0", "nginx": "1.25.3"}
        results = self.matcher.find_vulnerable_dependencies(deps, [fp])
        assert len(results) == 0

    def test_case_insensitive(self):
        fp = _make_fp(product="OpenSSL", versions=("3.2.*",))
        assert self.matcher.is_vulnerable("openssl", "3.2.1", fp) is True
