"""CLI entry point for restrictbot."""

import argparse
import csv
import json
import sys
from pathlib import Path

from restrictbot.scanner import available_categories, scan_product, scan_products


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="restrictbot",
        description="US Physical AI Trade Restriction Compliance Scanner",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # check command
    check_parser = subparsers.add_parser("check", help="Check a single product")
    check_parser.add_argument("name", help="Product name")
    check_parser.add_argument("description", help="Product description")
    check_parser.add_argument("--json", action="store_true", help="JSON output")
    check_parser.add_argument("--ci", action="store_true", help="CI gate: exit 1 on FAIL")

    # scan command (CSV batch)
    scan_parser = subparsers.add_parser("scan", help="Scan a CSV of products")
    scan_parser.add_argument("csv_file", help="Path to CSV file (columns: name,description)")
    scan_parser.add_argument("--json", action="store_true", help="JSON output")
    scan_parser.add_argument("--ci", action="store_true", help="CI gate: exit 1 on any FAIL")

    # categories command
    subparsers.add_parser("categories", help="List restricted categories")

    args = parser.parse_args()

    if args.command == "check":
        return _check(args.name, args.description, args.json, args.ci)
    elif args.command == "scan":
        return _scan(args.csv_file, args.json, args.ci)
    elif args.command == "categories":
        return _list_categories()
    return 0


def _check(name: str, description: str, json_output: bool, ci: bool) -> int:
    result = scan_product(name, description)
    if json_output:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        _print_result(result)

    if ci and result.verdict.value == "fail":
        return 1
    return 0


def _scan(csv_path: str, json_output: bool, ci: bool) -> int:
    path = Path(csv_path)
    if not path.exists():
        print(f"restrictbot: error: file not found: {csv_path}", file=sys.stderr)
        return 1

    products: list[tuple[str, str]] = []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
            if "name" not in header or "description" not in header:
                print("restrictbot: error: CSV must have 'name' and 'description' columns", file=sys.stderr)
                return 1
            name_idx = header.index("name")
            desc_idx = header.index("description")
        except StopIteration:
            print("restrictbot: error: empty CSV", file=sys.stderr)
            return 1
        for row in reader:
            if len(row) > max(name_idx, desc_idx):
                products.append((row[name_idx], row[desc_idx]))

    if not products:
        print("restrictbot: warning: no valid product rows found", file=sys.stderr)

    results = scan_products(products)

    if json_output:
        print(json.dumps([r.to_dict() for r in results], indent=2))
    else:
        for r in results:
            print()
            _print_result(r)

    if ci and any(r.verdict.value == "fail" for r in results):
        return 1
    return 0


def _list_categories() -> int:
    print("Restricted Categories (USG 2026-07-29 ban):")
    print("=" * 60)
    for cat in available_categories():
        label = f"[{cat.level.value.upper()}]"
        print(f"  {label:10s} {cat.name}")
        print(f"  {'':10s} {cat.description}")
        print(f"  {'':10s} Keywords: {', '.join(cat.keywords[:4])}")
        print()
    return 0


def _print_result(result) -> None:
    verdict_color = _color(result.verdict.value)
    print(f"  {result.product_name}")
    print(f"  Verdict: {verdict_color}{result.verdict.value.upper()}{_RESET}  Score: {result.score:.2f}")
    if result.findings:
        for f in result.findings:
            fv = _color(f.verdict.value)
            print(f"  {fv}[{f.verdict.value.upper()}]{_RESET} {f.category}: {f.reason}")
    else:
        print(f"  {_GREEN}No restrictions detected.{_RESET}")


_RESET = "\033[0m"
_RED = "\033[91m"
_YELLOW = "\033[93m"
_GREEN = "\033[92m"


def _color(verdict: str) -> str:
    if verdict == "fail":
        return _RED
    elif verdict == "warn":
        return _YELLOW
    return _GREEN


if __name__ == "__main__":
    sys.exit(main())