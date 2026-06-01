"""Scanner engine for AI Leak Scanner.

Scans a user's AI extension/installation profile against the vulnerability
database and generates a risk report.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone

from .vulndb import (
    Vulnerability,
    Severity,
    VULNERABILITIES,
    get_unpatched,
)


@dataclass
class ScanFinding:
    vulnerability: Vulnerability
    detected: bool
    confidence: float  # 0.0 - 1.0
    detail: str = ""


@dataclass
class ScanReport:
    scan_id: str
    timestamp: str
    target: str
    findings: list[ScanFinding]
    risk_score: float  # 0 - 100
    summary: str = ""

    @property
    def critical_count(self) -> int:
        return sum(
            1 for f in self.findings
            if f.detected and f.vulnerability.severity == Severity.CRITICAL
        )

    @property
    def high_count(self) -> int:
        return sum(
            1 for f in self.findings
            if f.detected and f.vulnerability.severity == Severity.HIGH
        )

    @property
    def medium_count(self) -> int:
        return sum(
            1 for f in self.findings
            if f.detected and f.vulnerability.severity == Severity.MEDIUM
        )

    @property
    def low_count(self) -> int:
        return sum(
            1 for f in self.findings
            if f.detected and f.vulnerability.severity == Severity.LOW
        )

    @property
    def total_detected(self) -> int:
        return sum(1 for f in self.findings if f.detected)

    @property
    def unpatched_detected(self) -> int:
        return sum(1 for f in self.findings if f.detected and not f.vulnerability.patched)


def _generate_scan_id() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"SCAN-{ts}"


def _calculate_risk_score(findings: list[ScanFinding]) -> float:
    """Calculate a 0-100 risk score based on detected vulnerabilities."""
    weights = {
        Severity.CRITICAL: 25.0,
        Severity.HIGH: 15.0,
        Severity.MEDIUM: 8.0,
        Severity.LOW: 3.0,
        Severity.INFO: 0.5,
    }
    score = 0.0
    for f in findings:
        if f.detected:
            base = weights.get(f.vulnerability.severity, 5.0)
            # Unpatched vulnerabilities score higher
            if not f.vulnerability.patched:
                base *= 1.5
            score += base * f.confidence
    return min(score, 100.0)


def _generate_summary(report: ScanReport) -> str:
    parts = []
    if report.critical_count > 0:
        parts.append(f"{report.critical_count} critical")
    if report.high_count > 0:
        parts.append(f"{report.high_count} high")
    if report.medium_count > 0:
        parts.append(f"{report.medium_count} medium")
    if report.low_count > 0:
        parts.append(f"{report.low_count} low")

    if not parts:
        return "No AI data exfiltration vulnerabilities detected."

    severity_str = ", ".join(parts)
    unpatched = report.unpatched_detected
    patched_note = ""
    if unpatched > 0:
        patched_note = f" ({unpatched} unpatched)"

    return (
        f"Detected {report.total_detected} vulnerabilities: "
        f"{severity_str}{patched_note}."
    )


def scan_extensions(
    installed: list[str],
    target_name: str = "local",
) -> ScanReport:
    """
    Scan a list of installed AI extensions/agents against the vuln database.

    Args:
        installed: List of product names (e.g., ["ChatGPT for Google Sheets", "Claude Cowork"])
        target_name: Name for the scan target (for reporting)

    Returns:
        ScanReport with findings and risk score
    """
    findings: list[ScanFinding] = []
    installed_lower = {name.strip().lower() for name in installed}

    for vuln in VULNERABILITIES:
        detected = False
        confidence = 0.0
        vuln_product_lower = vuln.product.lower()
        vuln_vendor_lower = vuln.vendor.lower()

        for inst_name in installed_lower:
            # Exact or substring match on product name
            if inst_name in vuln_product_lower or vuln_product_lower in inst_name:
                detected = True
                confidence = 0.95
                break
            # Vendor name appears in installed name AND at least one other word overlaps
            if vuln_vendor_lower in inst_name:
                vuln_words = set(vuln_product_lower.split()) - {"ai"}
                inst_words = set(inst_name.split()) - {"ai"}
                overlap = vuln_words & inst_words
                if len(overlap) >= 1:
                    detected = True
                    confidence = 0.85
                    break
            # Require multi-word overlap for non-vendor matches
            vuln_words = set(vuln_product_lower.split())
            inst_words = set(inst_name.split())
            overlap = vuln_words & inst_words
            # Must share at least 2 significant words (not just "ai")
            significant_overlap = overlap - {"ai", "for", "and", "the", "of", "in", "to"}
            if len(significant_overlap) >= 2:
                detected = True
                confidence = 0.7
                break

        findings.append(ScanFinding(
            vulnerability=vuln,
            detected=detected,
            confidence=confidence,
            detail=(
                f"{'DETECTED' if detected else 'not detected'}: "
                f"{vuln.vendor} {vuln.product}"
            ),
        ))

    scan_id = _generate_scan_id()
    timestamp = datetime.now(timezone.utc).isoformat()
    risk_score = _calculate_risk_score(findings)

    report = ScanReport(
        scan_id=scan_id,
        timestamp=timestamp,
        target=target_name,
        findings=findings,
        risk_score=risk_score,
    )
    report.summary = _generate_summary(report)
    return report


def scan_all() -> ScanReport:
    """
    Scan all known vulnerabilities (full database audit).
    Useful for generating a complete threat landscape report.
    """
    findings: list[ScanFinding] = []
    for vuln in VULNERABILITIES:
        findings.append(ScanFinding(
            vulnerability=vuln,
            detected=True,
            confidence=1.0,
            detail=f"Known vulnerability: {vuln.vendor} {vuln.product}",
        ))

    scan_id = _generate_scan_id()
    timestamp = datetime.now(timezone.utc).isoformat()
    risk_score = _calculate_risk_score(findings)

    report = ScanReport(
        scan_id=scan_id,
        timestamp=timestamp,
        target="full-database",
        findings=findings,
        risk_score=risk_score,
    )
    report.summary = _generate_summary(report)
    return report


def get_risk_level(score: float) -> str:
    """Convert a numeric risk score to a human-readable level."""
    if score >= 75:
        return "CRITICAL"
    elif score >= 50:
        return "HIGH"
    elif score >= 25:
        return "MEDIUM"
    elif score >= 10:
        return "LOW"
    else:
        return "MINIMAL"
