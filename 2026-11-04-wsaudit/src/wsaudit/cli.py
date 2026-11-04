"""Command line surface and the single exit contract.

    0  measured and clean      (digest computed / models identical)
    1  measured and disagreeing (manifest mismatch / models differ)
    2  could not measure        (unknown format, truncation, bad manifest)

Exit code 2 always outranks 0 and 1: "could not measure" is never clean.
"""

import argparse

from . import diff, digest, manifest, report
from .errors import WsAuditError

EXIT_OK = 0
EXIT_FINDING = 1
EXIT_UNMEASURED = 2


def build_parser():
    parser = argparse.ArgumentParser(
        prog="wsaudit",
        description="Per-tensor digests and diffs for safetensors and GGUF weights.",
    )
    sub = parser.add_subparsers(dest="command")

    hash_cmd = sub.add_parser("hash", help="digest a model file per tensor")
    hash_cmd.add_argument("model", help="path to a .safetensors or .gguf file")
    hash_cmd.add_argument("--json", action="store_true", help="machine-readable output")
    hash_cmd.add_argument("--quiet", action="store_true", help="exit code only")
    hash_cmd.add_argument("--header-only", action="store_true",
                          help="digest names/dtypes/shapes only (marked PARTIAL)")
    hash_cmd.add_argument("--manifest", metavar="PATH",
                          help="verify against a manifest written by --manifest-out")
    hash_cmd.add_argument("--manifest-out", metavar="PATH",
                          help="write this model's manifest for later verification")

    diff_cmd = sub.add_parser("diff", help="compare two model files tensor by tensor")
    diff_cmd.add_argument("base")
    diff_cmd.add_argument("other")
    diff_cmd.add_argument("--json", action="store_true")
    diff_cmd.add_argument("--quiet", action="store_true")
    diff_cmd.add_argument("--lora-map", action="store_true",
                          help="map lora_A/lora_B tensors back to the module they patch")
    diff_cmd.add_argument("--top", type=int, default=None,
                          help="print at most N rows")
    return parser


def _hash(args):
    model = digest.digest_model(args.model, header_only=args.header_only)
    if args.manifest_out:
        manifest.save_manifest(manifest.build_manifest(model), args.manifest_out)

    comparison = None
    if args.manifest:
        comparison = manifest.load_and_compare(model, args.manifest)
        if model.partial:
            print(
                "wsaudit: could not measure a verifiable digest - this was a partial "
                "(header-only) scan, so the manifest cannot be checked"
            )
            return EXIT_UNMEASURED
        code = EXIT_OK if comparison.ok else EXIT_FINDING
    else:
        code = EXIT_OK

    if args.json:
        print(report.dumps(report.hash_json(model, comparison)))
    elif not args.quiet:
        print(report.hash_text(model, comparison, args.manifest))
    return code


def _diff(args):
    result = diff.diff_models(args.base, args.other, lora_map=args.lora_map)
    code = EXIT_OK if not result.rows else EXIT_FINDING
    if args.json:
        print(report.dumps(report.diff_json(result)))
    elif not args.quiet:
        print(report.diff_text(result, top=args.top))
    return code


def main(argv=None):
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return EXIT_UNMEASURED
    try:
        if args.command == "hash":
            return _hash(args)
        if args.command == "diff":
            return _diff(args)
    except WsAuditError as exc:
        print("wsaudit: could not measure - %s" % exc)
        return EXIT_UNMEASURED
    parser.print_help()
    return EXIT_UNMEASURED
