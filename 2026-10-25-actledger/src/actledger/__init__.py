"""actledger — an agent action evidence ledger an outsider can re-verify."""

from .audit import AuditReport, audit, is_consequential
from .chain import GENESIS_HASH, canonical_json, entry_hash, sha256_hex, verify_entries
from .export import BUNDLE_FORMAT, build_bundle, bundle_digest, verify_bundle
from .ledger import Ledger, LedgerError
from .models import ActionRecord, AuditFinding, Entry, Severity

__version__ = "1.0.0"

__all__ = [
    "ActionRecord",
    "AuditFinding",
    "AuditReport",
    "BUNDLE_FORMAT",
    "Entry",
    "GENESIS_HASH",
    "Ledger",
    "LedgerError",
    "Severity",
    "audit",
    "build_bundle",
    "bundle_digest",
    "canonical_json",
    "entry_hash",
    "is_consequential",
    "sha256_hex",
    "verify_bundle",
    "verify_entries",
]
