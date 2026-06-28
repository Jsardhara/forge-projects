"""Scanner for detecting 0-day exploit repositories on GitHub."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional

from zerosentinel.models import (
    ExploitRepositry,
    Severity,
    VulnerabilityFingerprint,
)

# Patterns that indicate 0-day / exploit repositories
_ZERO_DAY_TOPICS = frozenset({
    "0-day", "0day", "zero-day", "zero-day-exploit",
    "exploit", "exploits", "poc", "proof-of-concept",
    "cve", "vulnerability", "rce", "remote-code-execution",
})

_EXPLOIT_README_PATTERNS = [
    re.compile(r"(?i)(0-day|zero.day|undisclosed)\s+(?:vulnerability|exploit|cve)"),
    re.compile(r"(?i)(?:remote|arbitrary)\s+code\s+execution"),
    re.compile(r"(?i)(?:privilege|root)\s+escalation"),
    re.compile(r"(?i)buffer\s+overflow"),
    re.compile(r"(?i)sql\s+injection"),
    re.compile(r"(?i)(?:xss|cross.site)\s*(?:script|injection)"),
    re.compile(r"(?i)(?:rce|rfi|lfi|xxe)\s*(?:poc|exploit)"),
    re.compile(r"(?i)(?:unauthenticated|unauth)\s+(?:access|bypass)"),
    re.compile(r"(?i)(?:authentication|auth)\s+bypass"),
    re.compile(r"(?i)directory\s+traversal"),
    re.compile(r"(?i)ssrf\s*(?:to|->)\s*(?:rce|lfi)"),
    re.compile(r"(?i)prototype\s+pollution"),
    re.compile(r"(?i)deserialization"),
    re.compile(r"(?i)race\s+condition"),
    re.compile(r"(?i)use.after.free|uaf"),
    re.compile(r"(?i)heap\s+(?:overflow|corruption)"),
    re.compile(r"(?i)stack\s+smashing"),
    re.compile(r"(?i)kernel\s+(?:exploit|pwn)"),
    re.compile(r"(?i)jailbreak"),
    re.compile(r"(?i)sandbox\s+escape"),
    re.compile(r"(?i)supply.chain"),
]

_CVE_PATTERN = re.compile(r"CVE-\d{4}-\d{4,7}")

# Product/version extraction patterns
_VERSION_PATTERNS = [
    re.compile(r"(?:affects?|vulnerable|impacted?)[\s:]+(.+?)\s+(?:<|<=|through|before)\s+(?:version\s+)?([\d.]+)", re.I),
    re.compile(r"(?:versions?|through)\s+([\d.]+)\s+(?:to|<)\s+([\d.]+)", re.I),
    re.compile(r"([\d.]+)\s*[-–]\s*([\d.]+)", re.I),
]

_PRODUCT_KEYWORDS = [
    "linux", "windows", "macos", "ios", "android", "chrome", "firefox",
    "safari", "edge", "apache", "nginx", "openssl", "openssh", "mysql",
    "postgresql", "redis", "mongodb", "elasticsearch", "docker", "kubernetes",
    "wordpress", "drupal", "joomla", "next.js", "react", "vue", "angular",
    "fastapi", "django", "flask", "spring", "rails", "laravel", "express",
    "tensorflow", "pytorch", "opencv", "nginx", "haproxy", "traefik",
    "intel", "amd", "nvidia", "apple", "qualcomm", "broadcom", "samsung",
    "cisco", "juniper", "fortinet", "paloalto", "f5", "vmware",
]


class ZeroDayScanner:
    """Scans for 0-day exploit repositories and extracts vulnerability fingerprints."""

    def __init__(
        self,
        severity_threshold: Severity = Severity.MEDIUM,
        max_readme_chars: int = 5000,
    ):
        self.severity_threshold = severity_threshold
        self.max_readme_chars = max_readme_chars

    def scan_repo(self, repo: ExploitRepositry) -> Optional[VulnerabilityFingerprint]:
        """Analyze a single repository for 0-day indicators."""
        if not self._is_likely_zero_day(repo):
            return None

        readme = repo.raw_readme[:self.max_readme_chars] if repo.raw_readme else ""
        description = repo.description or ""

        # Extract CVE ID if present
        cve_match = self._extract_cve(readme, description)
        cve_id = cve_match if cve_match else None

        # Extract affected product
        product = self._extract_product(readme, description, repo.name)
        if not product:
            product = repo.name

        # Extract affected versions
        versions = self._extract_versions(readme, description)

        # Determine vulnerability type
        vuln_type = self._classify_vulnerability_type(readme, description, repo.topics)

        # Determine severity
        severity = self._assess_severity(readme, description, repo.topics, repo.stars)

        # Extract CPEs
        cpes = self._extract_cpes(readme)

        # Extract references
        refs = self._extract_references(readme)

        # Build summary
        summary = self._build_summary(repo, vuln_type, product)

        return VulnerabilityFingerprint(
            cve_id=cve_id,
            affected_product=product,
            affected_versions=tuple(versions),
            vulnerability_type=vuln_type,
            severity=severity,
            summary=summary,
            extracted_cpes=tuple(cpes),
            references=tuple(refs),
        )

    def scan_batch(
        self,
        repos: list[ExploitRepositry],
    ) -> list[VulnerabilityFingerprint]:
        """Scan multiple repositories, returning only those with detected 0-day indicators."""
        results: list[VulnerabilityFingerprint] = []
        seen_keys: set[str] = set()

        for repo in repos:
            fingerprint = self.scan_repo(repo)
            if fingerprint and fingerprint.fingerprint_key not in seen_keys:
                seen_keys.add(fingerprint.fingerprint_key)
                results.append(fingerprint)

        return results

    def _is_likely_zero_day(self, repo: ExploitRepositry) -> bool:
        """Quick filter: does this repo look like a 0-day/exploit repo?"""
        # Check topics first (fastest)
        if _ZERO_DAY_TOPICS & set(repo.topics):
            return True

        # Check description
        desc_lower = (repo.description or "").lower()
        if any(topic in desc_lower for topic in _ZERO_DAY_TOPICS):
            # Filter out negated mentions ("not an exploit", "no 0-day")
            if not re.search(r"\b(no|not|without|isn't|aren't|non-)\b.*(?:exploit|0day|0-day|vulnerability)", desc_lower):
                return True

        # Check name
        name_lower = repo.name.lower()
        if any(kw in name_lower for kw in ("exploit", "0day", "0-day", "poc", "cve-")):
            return True

        # Check README for exploit patterns
        readme = (repo.raw_readme or "")[:2000].lower()
        if any(p.search(readme) for p in _EXPLOIT_README_PATTERNS[:5]):
            return True

        return False

    def _extract_cve(self, readme: str, description: str) -> Optional[str]:
        """Extract CVE ID from text."""
        for text in (readme, description):
            match = _CVE_PATTERN.search(text)
            if match:
                return match.group(0)
        return None

    def _extract_product(self, readme: str, description: str, repo_name: str) -> Optional[str]:
        """Extract the affected product name from text."""
        combined = f"{readme} {description}"

        for product in _PRODUCT_KEYWORDS:
            if product in combined.lower():
                return product

        # Try to extract from repo name (e.g., "cve-2026-xxxx-linux" → "linux")
        name_parts = re.split(r"[-_]", repo_name.lower())
        for part in name_parts:
            if part in _PRODUCT_KEYWORDS:
                return part

        return None

    def _extract_versions(self, readme: str, description: str) -> list[str]:
        """Extract affected version ranges."""
        combined = f"{readme} {description}"
        versions: list[str] = []

        for pattern in _VERSION_PATTERNS:
            for match in pattern.finditer(combined):
                for group in match.groups():
                    if group and re.match(r"[\d.]+", group):
                        versions.append(group)

        return list(dict.fromkeys(versions))  # dedupe preserving order

    def _classify_vulnerability_type(
        self, readme: str, description: str, topics: tuple[str, ...]
    ) -> str:
        """Classify the type of vulnerability."""
        combined = f"{readme} {description} {' '.join(topics)}".lower()

        type_patterns = [
            ("rce", ["remote code execution", "rce", "arbitrary code execution", "ace"]),
            ("xss", ["cross-site scripting", "xss", "dom xss", "reflected xss"]),
            ("sql_injection", ["sql injection", "sqli", "blind sql", "union-based"]),
            ("authentication_bypass", ["auth bypass", "authentication bypass", "unauth access"]),
            ("privilege_escalation", ["privilege escalation", "root escalation", "lpe", "kernel exploit"]),
            ("buffer_overflow", ["buffer overflow", "stack overflow", "heap overflow", "oob"]),
            ("directory_traversal", ["directory traversal", "path traversal", "lfi", "file inclusion"]),
            ("ssrf", ["ssrf", "server-side request forgery"]),
            ("deserialization", ["deserialization", "unsafe deserialization", "object injection"]),
            ("race_condition", ["race condition", "toctou", "time-of-check"]),
            ("use_after_free", ["use-after-free", "uaf", "double free"]),
            ("supply_chain", ["supply chain", "dependency confusion", "typosquat"]),
            ("memory_corruption", ["memory corruption", "heap corruption", "stack smashing"]),
            ("sandbox_escape", ["sandbox escape", "jailbreak", "container escape"]),
            ("kernel", ["kernel exploit", "kernel pwn", "ring0"]),
        ]

        for vuln_type, keywords in type_patterns:
            if any(kw in combined for kw in keywords):
                return vuln_type

        return "unknown"

    def _assess_severity(
        self, readme: str, description: str, topics: tuple[str, ...], stars: int
    ) -> Severity:
        """Assess severity based on exploit indicators."""
        combined = f"{readme} {description} {' '.join(topics)}".lower()

        critical_indicators = [
            "remote code execution", "rce", "kernel exploit", "sandbox escape",
            "authentication bypass", "unauthenticated rce", "wormable",
            "actively exploited", "in-the-wild", "zero-click",
        ]
        high_indicators = [
            "privilege escalation", "buffer overflow", "sql injection",
            "deserialization", "heap overflow", "use-after-free",
        ]
        medium_indicators = [
            "xss", "directory traversal", "ssrf", "race condition",
            "information disclosure", "denial of service", "dos",
        ]

        if any(kw in combined for kw in critical_indicators):
            return Severity.CRITICAL
        if any(kw in combined for kw in high_indicators):
            return Severity.HIGH
        if any(kw in combined for kw in medium_indicators):
            return Severity.MEDIUM

        # High-star repos with exploit topics are at least HIGH
        if stars >= 50 and _ZERO_DAY_TOPICS & set(topics):
            return Severity.HIGH

        return Severity.LOW

    def _extract_cpes(self, readme: str) -> list[str]:
        """Extract CPE identifiers from text."""
        cpe_pattern = re.compile(r"cpe:2\.3:[aho]:[^:]+:[^:]+:[^:\s]+")
        return cpe_pattern.findall(readme)

    def _extract_references(self, readme: str) -> list[str]:
        """Extract reference URLs from text."""
        url_pattern = re.compile(r"https?://[^\s\])\"']+")
        return url_pattern.findall(readme)[:10]  # cap at 10 references

    def _build_summary(
        self, repo: ExploitRepositry, vuln_type: str, product: str
    ) -> str:
        """Build a human-readable summary."""
        type_display = vuln_type.replace("_", " ").title()
        return (
            f"{type_display} vulnerability detected in {product} "
            f"from repository {repo.owner}/{repo.name}"
        )
