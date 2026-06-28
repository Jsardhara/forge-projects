"""Report generator for 0-day detection results."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional

from zerosentinel.models import (
    DetectionResult,
    PatchSuggestion,
    Severity,
    VulnerabilityFingerprint,
)


class ReportGenerator:
    """Generates formatted reports from detection results."""

    def generate_text_report(self, result: DetectionResult) -> str:
        """Generate a human-readable text report."""
        lines: list[str] = []

        # Header
        lines.append("=" * 72)
        lines.append("  ZeroDaySentinel — 0-Day Vulnerability Detection Report")
        lines.append("=" * 72)
        lines.append("")

        # Summary
        ts = result.scan_timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")
        lines.append(f"Scan Time:        {ts}")
        lines.append(f"Repos Scanned:    {result.repos_scanned}")
        lines.append(f"Scan Duration:    {result.scan_duration_seconds:.2f}s")
        lines.append(f"Matches Found:    {len(result.matches)}")
        lines.append(f"Critical:         {result.critical_count}")
        lines.append("")

        if not result.matches:
            lines.append("No 0-day vulnerabilities detected in scanned repositories.")
            lines.append("")
            return "\n".join(lines)

        # Matches
        lines.append("-" * 72)
        lines.append("  DETECTED VULNERABILITIES")
        lines.append("-" * 72)
        lines.append("")

        for i, match in enumerate(result.matches, 1):
            severity_badge = self._severity_badge(match.severity)
            lines.append(f"  [{i}] {severity_badge} {match.summary}")
            lines.append(f"      Product:     {match.affected_product}")
            if match.affected_versions:
                lines.append(f"      Versions:    {', '.join(match.affected_versions)}")
            if match.cve_id:
                lines.append(f"      CVE:         {match.cve_id}")
            lines.append(f"      Type:        {match.vulnerability_type}")
            if match.extracted_cpes:
                lines.append(f"      CPEs:        {', '.join(match.extracted_cpes[:3])}")
            lines.append("")

        # Patch suggestions
        if result.patch_suggestions:
            lines.append("-" * 72)
            lines.append("  PATCH SUGGESTIONS")
            lines.append("-" * 72)
            lines.append("")

            for i, suggestion in enumerate(result.patch_suggestions, 1):
                conf_str = f"{suggestion.confidence:.0%}"
                lines.append(f"  [{i}] {suggestion.patch_type.upper()} (confidence: {conf_str}, effort: {suggestion.estimated_effort})")
                lines.append(f"      {suggestion.suggested_fix}")
                if suggestion.references:
                    lines.append(f"      References:  {', '.join(suggestion.references[:3])}")
                lines.append("")

        # Footer
        lines.append("=" * 72)
        lines.append("  End of Report")
        lines.append("=" * 72)

        return "\n".join(lines)

    def generate_json_report(self, result: DetectionResult) -> str:
        """Generate a JSON report."""
        data = {
            "scan_timestamp": result.scan_timestamp.isoformat(),
            "repos_scanned": result.repos_scanned,
            "scan_duration_seconds": result.scan_duration_seconds,
            "total_matches": len(result.matches),
            "critical_count": result.critical_count,
            "matches": [
                self._fingerprint_to_dict(fp) for fp in result.matches
            ],
            "patch_suggestions": [
                self._suggestion_to_dict(ps) for ps in result.patch_suggestions
            ],
        }
        return json.dumps(data, indent=2)

    def _fingerprint_to_dict(self, fp: VulnerabilityFingerprint) -> dict:
        return {
            "cve_id": fp.cve_id,
            "affected_product": fp.affected_product,
            "affected_versions": list(fp.affected_versions),
            "vulnerability_type": fp.vulnerability_type,
            "severity": fp.severity.value,
            "summary": fp.summary,
            "extracted_cpes": list(fp.extracted_cpes),
            "references": list(fp.references),
        }

    def _suggestion_to_dict(self, ps: PatchSuggestion) -> dict:
        return {
            "fingerprint": self._fingerprint_to_dict(ps.fingerprint),
            "confidence": ps.confidence,
            "suggested_fix": ps.suggested_fix,
            "patch_type": ps.patch_type,
            "estimated_effort": ps.estimated_effort,
            "references": list(ps.references),
        }

    @staticmethod
    def _severity_badge(severity: Severity) -> str:
        badges = {
            Severity.CRITICAL: "[CRITICAL]",
            Severity.HIGH: "[HIGH]    ",
            Severity.MEDIUM: "[MEDIUM]  ",
            Severity.LOW: "[UNKNOWN] ",
        }
        return badges.get(severity, "[UNKNOWN] ")
