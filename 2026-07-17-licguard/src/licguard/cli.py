"""LicGuard command-line interface."""

import argparse
import json
import sys

from licguard.engine import evaluate, evaluate_manifest
from licguard.licenses import REGISTRY
from licguard.models import DeploymentContext, Verdict


_STATUS_GLYPH = {
    "COMPLIANT": "[OK]",
    "NEEDS_REVIEW": "[??]",
    "NON_COMPLIANT": "[XX]",
}


def _print_verdict(v: Verdict) -> None:
    print(f"{_STATUS_GLYPH.get(v.status, '[--]')} {v.model_id}  ({v.status})")
    if v.license_key:
        print(f"    license: {v.license_key}")
    for r in v.reasons:
        print(f"    - {r}")


def cmd_list(args) -> int:
    print("Known model licenses (offline database):\n")
    for key in sorted(REGISTRY):
        ml = REGISTRY[key]
        lic = ml.license
        lic_name = lic.name if lic else "UNPUBLISHED / UNKNOWN"
        print(f"  {key:18s} {lic_name}")
    print(
        "\nReminder: canonical license text is authoritative. Verify before deploying."
    )
    return 0


def cmd_check(args) -> int:
    ctx = DeploymentContext(
        commercial=args.commercial,
        redistribute=args.redistribute,
        finetune=args.finetune,
        hosting=args.hosting,
        monthly_active_users=args.monthly_active_users,
        use_case=args.use_case or "",
    )
    v = evaluate(args.model, ctx)
    _print_verdict(v)
    # Non-compliant is a hard failure; needs-review still exits 0 (allowed, with warning).
    if v.status == "NON_COMPLIANT":
        return 1
    return 0


def cmd_scan(args) -> int:
    with open(args.manifest, encoding="utf-8") as fh:
        manifest = json.load(fh)
    verdicts = evaluate_manifest(manifest)
    bad = 0
    for v in verdicts:
        _print_verdict(v)
        if v.status == "NON_COMPLIANT":
            bad += 1
        print("")
    print(f"Scanned {len(verdicts)} model(s); {bad} non-compliant.")
    return 1 if bad else 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="licguard",
        description="Offline ML/AI model license compliance checker for open-weight deployments.",
    )
    sub = p.add_subparsers(dest="command")

    pl = sub.add_parser("list", help="List known model licenses")
    pl.set_defaults(func=cmd_list)

    pc = sub.add_parser("check", help="Check a single model + use case")
    pc.add_argument("--model", required=True, help="Model id, e.g. llama-3.1-8b")
    pc.add_argument("--commercial", action="store_true", help="Commercial use")
    pc.add_argument("--redistribute", action="store_true", help="Redistributing the model")
    pc.add_argument("--finetune", action="store_true", help="Fine-tuning the model")
    pc.add_argument("--hosting", action="store_true", help="Hosting inference for third parties")
    pc.add_argument("--monthly-active-users", type=int, default=None, help="MAU for threshold checks")
    pc.add_argument("--use-case", default="", help="Free-text use case (AUP scan)")
    pc.set_defaults(func=cmd_check)

    ps = sub.add_parser("scan", help="Scan a deployment manifest (JSON)")
    ps.add_argument("--manifest", required=True, help="Path to manifest JSON")
    ps.set_defaults(func=cmd_scan)

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if not getattr(args, "command", None):
        parser.print_help()
        return 1
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
