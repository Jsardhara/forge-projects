"""CLI for zkage-verify."""

from __future__ import annotations

import argparse
import sys

from zkage_verify import __version__
from zkage_verify.verifier import AgeVerifier
from zkage_verify.models import AgeThreshold


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="zkage-verify",
        description="Privacy-preserving age verification with ZK proofs",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    
    subparsers = parser.add_subparsers(dest="command")
    
    # Demo command
    demo_parser = subparsers.add_parser("demo", help="Run a full demo flow")
    demo_parser.add_argument(
        "--birth-year", type=int, default=2000,
        help="Subject birth year (default: 2000)",
    )
    demo_parser.add_argument(
        "--threshold", choices=["COPPA", "TEEN", "ADULT", "ALCOHOL_US"],
        default="ADULT", help="Age threshold to verify (default: ADULT)",
    )
    demo_parser.add_argument(
        "--current-year", type=int, default=2026,
        help="Current year (default: 2026)",
    )
    
    # Verify command
    verify_parser = subparsers.add_parser("verify", help="Verify an age threshold")
    verify_parser.add_argument("--birth-year", type=int, required=True)
    verify_parser.add_argument(
        "--threshold", choices=["COPPA", "TEEN", "ADULT", "ALCOHOL_US"],
        default="ADULT",
    )
    verify_parser.add_argument("--current-year", type=int, default=2026)
    
    args = parser.parse_args(argv)
    
    if args.command is None:
        parser.print_help()
        return 0
    
    if args.command == "demo":
        return _run_demo(args.birth_year, args.threshold, args.current_year)
    elif args.command == "verify":
        return _run_verify(args.birth_year, args.threshold, args.current_year)
    
    return 0


def _run_demo(birth_year: int, threshold_name: str, current_year: int) -> int:
    """Run a full demonstration of the age verification flow."""
    threshold = AgeThreshold[threshold_name]
    verifier = AgeVerifier(current_year=current_year)
    
    print(f"🔐 zkage-verify Demo")
    print(f"   Current year: {current_year}")
    print(f"   Threshold: {threshold_name} (>= {threshold.value} years)")
    print()
    
    # Issue credential
    cred = verifier.issue_credential(
        subject_id="demo-user-001",
        birth_year=birth_year,
        issuer_id="demo-issuer",
    )
    print(f"📋 Credential issued:")
    print(f"   Subject: {cred.subject_id}")
    print(f"   Issuer: {cred.issuer_id}")
    print(f"   Birth year: [HIDDEN — committed]")
    print()
    
    # Verify
    result = verifier.verify(cred, threshold)
    
    if result.is_valid:
        print(f"✅ {result.message}")
        print(f"   Nullifier: {result.nullifier.value[:16]}...")
        print(f"   Proof valid: {result.proof_valid}")
        print(f"   Nullifier spent: {result.nullifier_spent}")
        print()
        print("   → Platform learns: user is >= 18")
        print("   → Platform does NOT learn: exact birth year, identity")
        
        # Try double-spend
        print()
        print("🔄 Attempting double-spend (same credential)...")
        result2 = verifier.verify(cred, threshold)
        if not result2.is_valid and result2.nullifier_spent:
            print(f"   ❌ Blocked: {result2.message}")
    else:
        print(f"❌ Verification failed: {result.message}")
        return 1
    
    return 0


def _run_verify(birth_year: int, threshold_name: str, current_year: int) -> int:
    """Run a single verification."""
    threshold = AgeThreshold[threshold_name]
    verifier = AgeVerifier(current_year=current_year)
    
    cred = verifier.issue_credential(
        subject_id="cli-user",
        birth_year=birth_year,
        issuer_id="cli-issuer",
    )
    
    result = verifier.verify(cred, threshold)
    
    if result.is_valid:
        print(f"VALID: {result.message}")
        print(f"NULLIFIER: {result.nullifier.value}")
        return 0
    else:
        print(f"INVALID: {result.message}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
