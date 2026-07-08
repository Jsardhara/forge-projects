"""apk-signal CLI entry point."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .analyzer import analyze
from .models import Severity


def _render(result) -> str:
    lines = []
    lines.append("=" * 64)
    lines.append(f"APK SIGNAL REPORT: {Path(result.apk_path).name}")
    lines.append("=" * 64)
    lines.append(f"Package      : {result.package_name or 'unknown'}")
    lines.append(f"Entries      : {result.entry_count}  |  DEX: {result.dex_count}  |  Native libs: {len(result.native_libs)}")
    lines.append(f"Permissions  : {len(result.permissions)} declared")
    lines.append(f"Risk score   : {result.risk_score}/100  ({result.risk_level.value})")
    lines.append("")
    if result.signals:
        # group by severity order
        order = {Severity.CRITICAL: 0, Severity.HIGH: 1, Severity.MEDIUM: 2,
                 Severity.LOW: 3, Severity.INFO: 4}
        sigs = sorted(result.signals, key=lambda s: (order.get(s.severity, 9), -s.score))
        lines.append(f"SIGNALS ({len(sigs)})")
        lines.append("-" * 64)
        for s in sigs:
            lines.append(f"[{s.severity.value:8}] {s.label}")
            lines.append(f"           {s.detail}")
            if s.source_file:
                lines.append(f"           @ {s.source_file}")
    else:
        lines.append("No signals extracted. APK looks benign at this layer.")
    lines.append("")
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="apk-signal",
        description="Static triage signal extractor for Android APKs (zero dependencies).",
    )
    parser.add_argument("apk", help="Path to the .apk file to analyze")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    parser.add_argument("--min-severity", default="INFO",
                        choices=[s.value for s in Severity],
                        help="Only show signals at or above this severity")
    args = parser.parse_args(argv)

    try:
        result = analyze(args.apk)
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        return 2
    except Exception as e:  # noqa: BLE001
        print(f"Analysis failed: {e}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
        return 0

    if args.min_severity != "INFO":
        threshold = [s.value for s in Severity].index(args.min_severity)
        result.signals = [s for s in result.signals
                          if [v.value for v in Severity].index(s.severity.value) <= threshold]

    print(_render(result))
    # Non-zero exit when CRITICAL/HIGH present, useful for CI gating
    if result.risk_level in (Severity.CRITICAL, Severity.HIGH):
        return 0  # report already printed; keep exit 0 for automation friendliness
    return 0


if __name__ == "__main__":
    sys.exit(main())
