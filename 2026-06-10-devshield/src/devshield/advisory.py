"""GitHub Advisory Database client.

Queries the GitHub Advisory DB REST API for known vulnerabilities
in AI tooling packages. No authentication required for public advisories.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import requests


GITHUB_ADVISORY_URL = "https://api.github.com/advisories"
GITHUB_NPM_ADVISORY_URL = "https://api.github.com/advisories?ecosystem=npm"
GITHUB_PIP_ADVISORY_URL = "https://api.github.com/advisories?ecosystem=pip"

# Rate limit: 60 requests/hour for unauthenticated requests
RATE_LIMIT_DELAY = 60.0 / 60  # 1 request per second to be safe


@dataclass
class Advisory:
    """A single security advisory."""
    ghsa_id: str
    cve_id: str | None
    summary: str
    description: str
    severity: str
    url: str
    affected_packages: list[str] = field(default_factory=list)


@dataclass
class AdvisoryResult:
    """Result of an advisory lookup."""
    package_name: str
    ecosystem: str
    advisories: list[Advisory] = field(default_factory=list)
    error: str | None = None

    @property
    def is_vulnerable(self) -> bool:
        return len(self.advisories) > 0

    @property
    def max_severity(self) -> str:
        if not self.advisories:
            return "none"
        severity_order = {"critical": 4, "high": 3, "medium": 2, "low": 1, "none": 0}
        severities = {a.severity.lower() for a in self.advisories if a.severity}
        for sev in ("critical", "high", "medium", "low"):
            if sev in severities:
                return sev
        return "unknown"


class AdvisoryClient:
    """Client for the GitHub Advisory Database."""

    def __init__(self, token: str | None = None, timeout: int = 30):
        self.token = token
        self.timeout = timeout
        self._session = requests.Session()
        self._last_request_time = 0.0

        self._session.headers.update({
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        })
        if token:
            self._session.headers["Authorization"] = f"Bearer {token}"

    def _rate_limit(self):
        """Simple rate limiter."""
        now = time.monotonic()
        elapsed = now - self._last_request_time
        if elapsed < RATE_LIMIT_DELAY:
            time.sleep(RATE_LIMIT_DELAY - elapsed)
        self._last_request_time = time.monotonic()

    def _get(self, url: str, params: dict | None = None) -> dict | list:
        """Make a rate-limited GET request."""
        self._rate_limit()
        resp = self._session.get(url, params=params, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def search_by_package(
        self, package_name: str, ecosystem: str, max_results: int = 50
    ) -> AdvisoryResult:
        """Search advisories for a specific package."""
        result = AdvisoryResult(package_name=package_name, ecosystem=ecosystem)

        try:
            # GitHub Advisory API supports filtering by ecosystem
            # We fetch recent advisories and filter client-side for the package
            params = {
                "ecosystem": ecosystem,
                "per_page": min(max_results, 100),
                "direction": "desc",
                "sort": "updated",
            }

            advisories = self._get(GITHUB_ADVISORY_URL, params=params)

            if isinstance(advisories, list):
                for adv in advisories:
                    affected = adv.get("vulnerabilities", [])
                    for vuln in affected:
                        pkg = vuln.get("package", {})
                        if pkg.get("name", "").lower() == package_name.lower() and \
                           pkg.get("ecosystem", "").lower() == ecosystem.lower():
                            result.advisories.append(self._parse_advisory(adv))
                            break

        except requests.RequestException as e:
            result.error = str(e)

        return result

    def get_recent_advisories(self, ecosystem: str, days: int = 30) -> list[Advisory]:
        """Get recent advisories for an ecosystem."""
        params = {
            "ecosystem": ecosystem,
            "per_page": 100,
            "direction": "desc",
            "sort": "published",
        }

        try:
            advisories = self._get(GITHUB_ADVISORY_URL, params=params)
            if isinstance(advisories, list):
                return [self._parse_advisory(a) for a in advisories]
        except requests.RequestException:
            pass

        return []

    @staticmethod
    def _parse_advisory(data: dict) -> Advisory:
        """Parse advisory JSON into an Advisory object."""
        severity = data.get("severity", "unknown")
        cve_id = None
        for cid in data.get("identifiers", []):
            if cid.get("type") == "CVE":
                cve_id = cid.get("value")
                break

        affected_packages = []
        for vuln in data.get("vulnerabilities", []):
            pkg = vuln.get("package", {})
            name = pkg.get("name", "")
            eco = pkg.get("ecosystem", "")
            if name:
                affected_packages.append(f"{eco}/{name}")

        return Advisory(
            ghsa_id=data.get("ghsa_id", ""),
            cve_id=cve_id,
            summary=data.get("summary", ""),
            description=data.get("description", ""),
            severity=severity,
            url=data.get("html_url", ""),
            affected_packages=affected_packages,
        )

    def close(self):
        self._session.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
