"""AI Leak Scanner — Security audit tool for AI extensions and agents.

Scans installed AI tools against a database of known data exfiltration
vulnerabilities and generates risk reports.

Usage:
    # Scan specific extensions
    python -m ai_leak_scanner scan "ChatGPT for Google Sheets" "Claude Cowork"

    # Full database audit
    python -m ai_leak_scanner audit

    # Start API server
    python -m ai_leak_scanner serve
"""

import json
import sys

from .vulndb import VULNERABILITIES, get_unpatched, get_by_severity, Severity
from .scanner import scan_extensions, scan_all, get_risk_level


def cmd_scan(args: list[str]) -> None:
    """Scan installed extensions."""
    if not args:
        print("Usage: scan <extension-name> [extension-name ...]")
        sys.exit(1)

    report = scan_extensions(args)
    print(f"\n{'='*60}")
    print(f"  AI Leak Scanner — Scan Report")
    print(f"{'='*60}")
    print(f"  Scan ID:   {report.scan_id}")
    print(f"  Target:    {report.target}")
    print(f"  Time:      {report.timestamp}")
    print(f"  Risk:      {report.risk_score:.1f}/100 ({get_risk_level(report.risk_score)})")
    print(f"{'='*60}")
    print(f"  {report.summary}")
    print(f"{'='*60}\n")

    detected = [f for f in report.findings if f.detected]
    if detected:
        print("  DETECTED VULNERABILITIES:")
        print(f"  {'-'*56}")
        for f in detected:
            v = f.vulnerability
            status = "PATCHED" if v.patched else "UNPATCHED"
            print(f"  [{v.severity.value.upper():>8}] {v.id}  ({status})")
            print(f"             {v.vendor} — {v.product}")
            print(f"             {v.description[:80]}...")
            print(f"             Confidence: {f.confidence:.0%}")
            print()
    else:
        print("  No known vulnerabilities detected for these extensions.\n")


def cmd_audit(args: list[str]) -> None:
    """Full database audit."""
    report = scan_all()
    print(f"\n{'='*60}")
    print(f"  AI Leak Scanner — Full Threat Landscape")
    print(f"{'='*60}")
    print(f"  Total vulnerabilities in database: {len(VULNERABILITIES)}")
    print(f"  Unpatched: {len(get_unpatched())}")
    print(f"  Critical:  {len(get_by_severity(Severity.CRITICAL))}")
    print(f"  High:      {len(get_by_severity(Severity.HIGH))}")
    print(f"  Medium:    {len(get_by_severity(Severity.MEDIUM))}")
    print(f"{'='*60}\n")

    print("  ALL VULNERABILITIES:")
    print(f"  {'-'*56}")
    for v in VULNERABILITIES:
        status = "PATCHED" if v.patched else "UNPATCHED"
        print(f"  [{v.severity.value.upper():>8}] {v.id}  ({status})")
        print(f"             {v.vendor} — {v.product}")
        print()


def cmd_json(args: list[str]) -> None:
    """Output scan as JSON."""
    if not args:
        report = scan_all()
    else:
        report = scan_extensions(args)

    output = {
        "scan_id": report.scan_id,
        "timestamp": report.timestamp,
        "target": report.target,
        "risk_score": round(report.risk_score, 1),
        "risk_level": get_risk_level(report.risk_score),
        "summary": report.summary,
        "findings": [
            {
                "id": f.vulnerability.id,
                "vendor": f.vulnerability.vendor,
                "product": f.vulnerability.product,
                "severity": f.vulnerability.severity.value,
                "detected": f.detected,
                "confidence": f.confidence,
                "patched": f.vulnerability.patched,
                "description": f.vulnerability.description,
                "mitigation": f.vulnerability.mitigation,
            }
            for f in report.findings
        ],
    }
    print(json.dumps(output, indent=2))


def cmd_serve(args: list[str]) -> None:
    """Start the FastAPI server."""
    import uvicorn
    port = int(args[0]) if args else 8000
    from .app import app
    uvicorn.run(app, host="0.0.0.0", port=port)


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        print("Commands: scan, audit, json, serve")
        sys.exit(0)

    command = sys.argv[1]
    args = sys.argv[2:]

    commands = {
        "scan": cmd_scan,
        "audit": cmd_audit,
        "json": cmd_json,
        "serve": cmd_serve,
    }

    handler = commands.get(command)
    if handler is None:
        print(f"Unknown command: {command}")
        print(f"Available: {', '.join(commands)}")
        sys.exit(1)

    handler(args)


if __name__ == "__main__":
    main()
