# zkage-verify

**Privacy-preserving age verification with zero-knowledge proof primitives.**

Prove "user is ≥ 18" without revealing their exact birthdate. Compliant with KIDS Act, EU Chat Control, and UK OAIC requirements — without collecting PII.

## Why

Current age verification is broken:
- **ID upload** (Yoti, Jumio) → honeypot of identity data, breach liability
- **Self-declaration** → trivially bypassed, non-compliant
- **Apple Age Range API** → iOS-only, doesn't satisfy KIDS Act for all users

`zkage-verify` provides the cryptographic primitives for platforms to verify age thresholds while learning **nothing** about the user's actual birthdate.

## How It Works

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│ Trusted     │───▶│ ZK Proof     │───▶│ Platform    │
│ Issuer      │    │ (range proof)│    │ Verifier    │
│ (gov, bank) │    │              │    │             │
└─────────────┘    └──────────────┘    └─────────────┘
   Issues              Proves:              Learns:
   credential          age >= 18            ✅ threshold met
   (signed)            without              ❌ NOT birthdate
                       revealing            ❌ NOT identity
                       birthdate
```

### Cryptographic Primitives

1. **Pedersen Commitments** — perfectly hiding, computationally binding
2. **Range Proofs** (Bulletproofs-style) — prove `threshold ≤ value ≤ max` without revealing `value`
3. **Nullifier Scheme** — prevents credential reuse/double-spending across services

## Install

```bash
pip install .
```

## Quick Start

```python
from zkage_verify.verifier import AgeVerifier
from zkage_verify.models import AgeThreshold

# Initialize verifier
verifier = AgeVerifier(current_year=2026)

# Issue credential (trusted issuer does this)
cred = verifier.issue_credential(
    subject_id="user-123",
    birth_year=2000,
    issuer_id="gov-id-authority",
)

# Verify age >= 18
result = verifier.verify(cred, AgeThreshold.ADULT)

if result.is_valid:
    print("Access granted — age verified, no birthdate revealed")
    print(f"Nullifier: {result.nullifier.value[:16]}...")
```

## CLI

```bash
# Run demo
zkage-verify demo --birth-year 2000 --threshold ADULT

# Verify specific case
zkage-verify verify --birth-year 2010 --threshold COPPA
```

## API

### AgeVerifier

| Method | Description |
|--------|-------------|
| `issue_credential(subject_id, birth_year, issuer_id)` | Issue a new age credential |
| `verify(credential, threshold)` | Verify age >= threshold with ZK proof |

### AgeThreshold

| Threshold | Value | Use Case |
|-----------|-------|----------|
| `COPPA` | 13 | US children's privacy |
| `TEEN` | 16 | EU GDPR digital consent |
| `ADULT` | 18 | Adult content, gambling |
| `ALCOHOL_US` | 21 | US alcohol/tobacco |

## Compliance Mapping

| Regulation | Requirement | zkage-verify Approach |
|------------|-------------|----------------------|
| KIDS Act (US) | Age verification for internet access | ZK proof of age, no ID storage |
| EU Chat Control | Age-gated messaging | Nullifier-based verification |
| UK OAIC | Age-appropriate design | Range proof, minimal data collection |
| GDPR | Data minimization | Zero PII revealed to platform |

## Architecture

```
zkage_verify/
├── models.py        # Frozen dataclasses (AgeCredential, Proof, etc.)
├── commitment.py    # Pedersen commitment scheme
├── rangeproof.py    # Bulletproofs-style range proofs
├── nullifier.py     # Double-spend prevention
├── verifier.py      # High-level AgeVerifier engine
└── cli.py           # Command-line interface
```

## Limitations

- This is a **reference implementation** for the cryptographic primitives
- Production deployments should use a verified ZK library (bulletproofs-rs, circom/snarkjs)
- The simplified range proof demonstrates the concept but lacks the full inner-product argument of production Bulletproofs
- Trusted issuer infrastructure is out of scope (assumes existing PKI)

## License

MIT

## Source

Built from Lens Daily Intel 2026-06-29, Opportunity #2 (KIDS Act + EU Chat Control + age attribution signals).
