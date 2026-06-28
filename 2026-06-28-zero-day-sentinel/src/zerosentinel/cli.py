"""CLI for ZeroDaySentinel."""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timezone

from zerosentinel import (
    DependencyMatcher,
    PatchGenerator,
    ReportGenerator,
    ZeroDayScanner,
)
from zerosentinel.models import (
    DetectionResult,
    ExploitRepositry,
    Severity,
)


def _create_sample_repos() -> list[ExploitRepositry]:
    """Create sample exploit repos for demonstration."""
    return [
        ExploitRepositry(
            repo_id="r001",
            repo_url="https://github.com/anonymous/cve-2026-xxxx-linux",
            owner="anonymous",
            name="cve-2026-xxxx-linux",
            description="0-day remote code execution in Linux kernel < 6.8.0",
            published_at=datetime(2026, 6, 27, 14, 30, tzinfo=timezone.utc),
            topics=("0day", "exploit", "rce", "linux"),
            stars=234,
            language="C",
            raw_readme="""# CVE-2026-XXXX Linux Kernel RCE

## Summary
Remote code execution vulnerability in Linux kernel through race condition in netfilter.

## Affected Versions
Linux kernel < 6.8.0

## Severity
CVSS 9.8 - Critical

## Exploitation
This exploit triggers a use-after-free in the netfilter subsystem,
leading to arbitrary code execution in kernel mode.

## References
- https://nvd.nist.gov/vuln/detail/CVE-2026-XXXX
- https://example.com/advisory
""",
        ),
        ExploitRepositry(
            repo_id="r002",
            repo_url="https://github.com/bikini/exploitarium",
            owner="bikini",
            name="exploitarium",
            description="Collection of 0-day exploits for various products",
            published_at=datetime(2026, 6, 27, 10, 0, tzinfo=timezone.utc),
            topics=("exploit", "0day", "poc", "cve"),
            stars=1205,
            language="Python",
            raw_readme="""# Exploitarium

Mass 0-day exploit collection. Updated daily.

## Contents
- CVE-2026-YYYY: Apache HTTPD authentication bypass
- CVE-2026-ZZZZ: OpenSSL buffer overflow in TLS handshake
- CVE-2026-WWWW: Nginx RCE via SSRF

## Disclaimer
For educational purposes only.
""",
        ),
        ExploitRepositry(
            repo_id="r003",
            repo_url="https://github.com/user/random-tool",
            owner="user",
            name="random-tool",
            description="A random developer tool, not an exploit",
            published_at=datetime(2026, 6, 26, 8, 0, tzinfo=timezone.utc),
            topics=("tool", "developer"),
            stars=12,
            language="Python",
            raw_readme="""# Random Tool

Just a normal developer tool. Nothing to see here.
""",
        ),
    ]


def _create_sample_deps() -> dict[str, str]:
    """Create a sample dependency graph."""
    return {
        "linux": "6.7.0",
        "openssl": "3.2.1",
        "nginx": "1.25.3",
        "apache": "2.4.58",
        "postgresql": "16.2",
        "redis": "7.2.4",
        "python": "3.12.3",
    }


def main(argv: list[str] | None = None) -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="zerosentinel",
        description="ZeroDaySentinel — GitHub 0-Day Detection & Patch Automation",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # scan command
    scan_parser = subparsers.add_parser("scan", help="Scan repos for 0-day indicators")
    scan_parser.add_argument("--severity", choices=["critical", "high", "medium", "low"],
                               default="medium", help="Minimum severity threshold")
    scan_parser.add_argument("--format", choices=["text", "json"], default="text",
                              help="Output format")
    scan_parser.add_argument("--demo", action="store_true", help="Run with sample data")

    # match command
    match_parser = subparsers.add_parser("match", help="Match vulnerabilities against dependencies")
    match_parser.add_argument("--format", choices=["text", "json"], default="text")
    match_parser.add_argument("--demo", action="store_true")

    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 1

    scanner = ZeroDayScanner()
    matcher = DependencyMatcher()
    patch_gen = PatchGenerator()
    reporter = ReportGenerator()

    if args.command == "scan":
        if args.demo:
            repos = _create_sample_repos()
        else:
            print("No repos provided. Use --demo for demonstration.", file=sys.stderr)
            return 1

        severity_map = {
            "critical": Severity.CRITICAL,
            "high": Severity.HIGH,
            "medium": Severity.MEDIUM,
            "low": Severity.LOW,
        }
        scanner.severity_threshold = severity_map[args.severity]

        start = time.monotonic()
        fingerprints = scanner.scan_batch(repos)
        duration = time.monotonic() - start

        suggestions = patch_gen.generate_batch(fingerprints)
        result = DetectionResult(
            scan_timestamp=datetime.now(timezone.utc),
            repos_scanned=len(repos),
            matches=tuple(fingerprints),
            patch_suggestions=tuple(suggestions),
            scan_duration_seconds=duration,
        )

        if args.format == "json":
            print(reporter.generate_json_report(result))
        else:
            print(reporter.generate_text_report(result))

    elif args.command == "match":
        if args.demo:
            repos = _create_sample_repos()
            deps = _create_sample_deps()
        else:
            print("No data provided. Use --demo for demonstration.", file=sys.stderr)
            return 1

        fingerprints = scanner.scan_batch(repos)
        matches = matcher.find_vulnerable_dependencies(deps, fingerprints)

        if args.format == "json":
            output = [
                {
                    "package": pkg,
                    "version": ver,
                    "vulnerability": fp.summary,
                    "severity": fp.severity.value,
                }
                for pkg, ver, fp in matches
            ]
            import json
            print(json.dumps(output, indent=2))
        else:
            if not matches:
                print("No vulnerable dependencies found.")
            else:
                print(f"Found {len(matches)} vulnerable dependencies:\n")
                for pkg, ver, fp in matches:
                    print(f"  [{fp.severity.value.upper()}] {pkg} {ver}")
                    print(f"    {fp.summary}")
                    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
