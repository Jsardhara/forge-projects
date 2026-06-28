"""Dependency matcher — fingerprints vulnerabilities against a dependency graph."""

from __future__ import annotations

import re
from typing import Optional

from zerosentinel.models import VulnerabilityFingerprint

# Normalization map for product names that appear differently in CPEs vs dependencies
_PRODUCT_ALIASES = {
    "openssh": "openssh",
    "openbsd_openssh": "openssh",
    "openssl": "openssl",
    "libssl": "openssl",
    "nginx": "nginx",
    "apache": "apache",
    "httpd": "apache",
    "apache_httpd": "apache",
    "mysql": "mysql",
    "mariadb": "mysql",
    "postgresql": "postgresql",
    "postgres": "postgresql",
    "redis": "redis",
    "mongodb": "mongodb",
    "docker": "docker",
    "kubernetes": "kubernetes",
    "chrome": "chrome",
    "chromium": "chrome",
    "firefox": "firefox",
    "safari": "safari",
    "edge": "edge",
    "linux": "linux",
    "linux_kernel": "linux",
    "windows": "windows",
    "macos": "macos",
    "ios": "ios",
    "android": "android",
    "wordpress": "wordpress",
    "next.js": "next.js",
    "nextjs": "next.js",
    "react": "react",
    "vue": "vue",
    "angular": "angular",
    "fastapi": "fastapi",
    "django": "django",
    "flask": "flask",
    "tensorflow": "tensorflow",
    "pytorch": "pytorch",
    "opencv": "opencv",
    "openssl3": "openssl",
    "libreoffice": "libreoffice",
    "intel": "intel",
    "amd": "amd",
    "nvidia": "nvidia",
    "apple": "apple",
    "qualcomm": "qualcomm",
    "broadcom": "broadcom",
    "samsung": "samsung",
    "cisco": "cisco",
    "vmware": "vmware",
}

# Version comparison helpers
_VERSION_SEP = re.compile(r"[.\-_+]")


def _normalize_version(version: str) -> tuple[int, ...]:
    """Parse a version string into a comparable tuple of ints."""
    stripped = version.strip()
    if not stripped:
        return ()
    parts = _VERSION_SEP.split(stripped)
    result: list[int] = []
    for part in parts:
        try:
            result.append(int(part))
        except ValueError:
            # Non-numeric parts get treated as 0 for comparison
            result.append(0)
    return tuple(result)


def _version_matches_range(
    version: str, affected_versions: tuple[str, ...]
) -> bool:
    """Check if a version falls within any of the affected version ranges."""
    if not affected_versions:
        return True  # No version constraint = affects all

    v_normalized = _normalize_version(version)

    for av in affected_versions:
        av_clean = av.strip()
        if av_clean.endswith("*"):
            # Prefix match: "1.2.*" matches "1.2.3"
            prefix = _normalize_version(av_clean[:-1].rstrip("."))
            if v_normalized[:len(prefix)] == prefix:
                return True
        elif " - " in av_clean or " to " in av_clean.lower():
            # Range: "1.0 - 2.0" or "1.0 to 2.0"
            sep = " - " if " - " in av_clean else " to "
            parts = av_clean.split(sep)
            if len(parts) == 2:
                low = _normalize_version(parts[0])
                high = _normalize_version(parts[1])
                if low <= v_normalized <= high:
                    return True
        else:
            # Exact match
            if _normalize_version(av_clean) == v_normalized:
                return True

    return False


def _normalize_product(product: str) -> str:
    """Normalize a product name for matching."""
    key = product.lower().strip()
    return _PRODUCT_ALIASES.get(key, key)


class DependencyMatcher:
    """Matches vulnerability fingerprints against a dependency graph."""

    def __init__(self, case_sensitive: bool = False):
        self.case_sensitive = case_sensitive

    def is_vulnerable(
        self,
        dependency_name: str,
        dependency_version: str,
        fingerprint: VulnerabilityFingerprint,
    ) -> bool:
        """Check if a specific dependency version is vulnerable according to the fingerprint."""
        # Normalize names for matching
        dep_norm = dependency_name if self.case_sensitive else dependency_name.lower()
        prod_norm = fingerprint.affected_product if self.case_sensitive else fingerprint.affected_product.lower()

        # Direct match
        if dep_norm == prod_norm:
            return _version_matches_range(dependency_version, fingerprint.affected_versions)

        # Alias match
        dep_alias = _normalize_product(dep_norm)
        prod_alias = _normalize_product(prod_norm)
        if dep_alias == prod_alias:
            return _version_matches_range(dependency_version, fingerprint.affected_versions)

        # CPE match
        for cpe in fingerprint.extracted_cpes:
            cpe_lower = cpe.lower()
            if dep_norm in cpe_lower or prod_norm in cpe_lower:
                return _version_matches_range(dependency_version, fingerprint.affected_versions)

        # Substring match (e.g., "libssl1.1" matches "openssl")
        if len(dep_norm) > 3 and (dep_norm in prod_norm or prod_norm in dep_norm):
            return _version_matches_range(dependency_version, fingerprint.affected_versions)

        return False

    def find_vulnerable_dependencies(
        self,
        dependencies: dict[str, str],
        fingerprints: list[VulnerabilityFingerprint],
    ) -> list[tuple[str, str, VulnerabilityFingerprint]]:
        """Find all vulnerable dependencies in a dependency graph.

        Args:
            dependencies: Dict mapping package_name → version
            fingerprints: List of vulnerability fingerprints to check against

        Returns:
            List of (package_name, version, matching_fingerprint) tuples
        """
        results: list[tuple[str, str, VulnerabilityFingerprint]] = []

        for pkg_name, pkg_version in dependencies.items():
            for fp in fingerprints:
                if self.is_vulnerable(pkg_name, pkg_version, fp):
                    results.append((pkg_name, pkg_version, fp))

        return results
