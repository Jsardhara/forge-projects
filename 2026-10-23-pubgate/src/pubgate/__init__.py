"""pubgate — published-artifact provenance gate.

One assertion, verifiable offline:

    published artifact == build(upstream source)
"""

__version__ = "0.1.0"

from pubgate.engine import (  # noqa: F401
    MANIFEST_SCHEMA,
    PubgateError,
    Violation,
    exit_code,
    iau_digest,
    record_hashes,
    sha256_bytes,
    source_manifest,
    verify_record,
    verify_source,
)
