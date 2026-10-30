"""Command line: exit 0 clean, 1 findings, 2 unmeasurable. Same contract as
kvpreflight and tsattest so all three roll into one fleet report.
"""
import argparse
import sys
from pathlib import Path

from .scan import scan

PROG = "secretsurface"


def default_roots(home: Path) -> list:
    """The surfaces that actually carry key material on an agent host."""
    return [
        home / ".hermes" / "profiles",
        home / ".hermes" / "skills",
        home / "code" / "jarmes",
    ]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=PROG,
        description="Report where key material actually lives, by class. "
                    "Read-only; never prints a secret.",
    )
    parser.add_argument("roots", nargs="*", metavar="ROOT",
                        help="paths to scan (default: ~/.hermes/profiles, "
                             "~/.hermes/skills, ~/code/jarmes)")
    parser.add_argument("--json", action="store_true", dest="as_json",
                        help="machine-readable rollup")
    parser.add_argument("--revoke-list", action="store_true", dest="revoke",
                        help="print only the paths to rotate from")
    parser.add_argument("--quiet", action="store_true",
                        help="say nothing when the verdict is clean")
    parser.add_argument("--max-bytes", type=int, default=None,
                        help="skip files larger than this (default 4000000)")
    parser.add_argument("--version", action="version", version="%(prog)s 1.0.0")
    return parser


def main(argv=None) -> int:
    parser = _build_parser()
    try:
        args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))
    except SystemExit as exc:  # argparse exits; keep main() returning an int
        return int(exc.code or 0)

    roots = [Path(root).expanduser() for root in args.roots]
    if not roots:
        roots = default_roots(Path.home())

    kwargs = {} if args.max_bytes is None else {"max_bytes": args.max_bytes}
    report = scan(roots, **kwargs)

    if args.revoke:
        paths = report.revoke_list()
        if paths:
            print("\n".join(paths))
    elif args.as_json:
        print(report.as_json())
    elif not (args.quiet and report.is_clean()):
        sys.stdout.write(report.as_text())

    return report.exit_code()


def entry() -> None:
    raise SystemExit(main())
