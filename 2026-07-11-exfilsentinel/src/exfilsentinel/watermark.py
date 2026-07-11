from __future__ import annotations

from datetime import datetime, timezone

from .models import ProvenanceRecord, Watermark

# Four distinct zero-width Unicode chars.
# A/B are reserved EXCLUSIVELY for framing delimiters so they can never
# appear inside the bit payload (which uses only C/D). This prevents the
# postamble sequence from being falsely matched inside the encoded bits.
_A = "\u200b"  # ZWSP  (framing only)
_B = "\u200c"  # ZWNJ  (framing only)
_C = "\u200d"  # ZWJ   -> bit 0
_D = "\u2060"  # WORD JOINER -> bit 1

PREAMBLE = _A + _B
POSTAMBLE = _B + _A
_BITS_PER_BYTE = 8


def _payload_of(record: ProvenanceRecord) -> str:
    ts = record.issued_at
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return f"{record.org_id}|{record.model}|{ts.isoformat()}|{record.nonce}"


def _encode_bits(payload: str) -> str:
    data = payload.encode("utf-8")
    out: list[str] = []
    for byte in data:
        for i in range(_BITS_PER_BYTE):
            bit = (byte >> (7 - i)) & 1
            out.append(_D if bit else _C)
    return "".join(out)


def _decode_bits(zw: str) -> str:
    bits: list[int] = []
    for ch in zw:
        if ch == _C:
            bits.append(0)
        elif ch == _D:
            bits.append(1)
        else:
            raise ValueError("unexpected char in watermark region")
    if len(bits) % 8 != 0:
        raise ValueError("bit count not multiple of 8")
    out = bytearray()
    for i in range(0, len(bits), 8):
        byte = 0
        for b in bits[i : i + 8]:
            byte = (byte << 1) | b
        out.append(byte)
    return out.decode("utf-8")


def embed(text: str, record: ProvenanceRecord) -> Watermark:
    """Embed an invisible provenance record into text (survives copy-paste)."""
    payload = _payload_of(record)
    bits = _encode_bits(payload)
    watermarked = text + PREAMBLE + bits + POSTAMBLE
    payload_bits = "".join("1" if c == _D else "0" for c in bits)
    return Watermark(record=record, payload_bits=payload_bits, text=watermarked)


def _extract_region(text: str):
    start = text.find(PREAMBLE)
    if start == -1:
        return None
    after_start = start + len(PREAMBLE)
    end = text.find(POSTAMBLE, after_start)
    if end == -1:
        return None
    return text[after_start:end]


def detect(text: str) -> bool:
    """Return True if text carries a decodable provenance watermark."""
    region = _extract_region(text)
    if region is None:
        return False
    try:
        _decode_bits(region)
        return True
    except Exception:
        return False


def verify(text: str):
    """Extract and decode the provenance record, or None if absent/invalid."""
    region = _extract_region(text)
    if region is None:
        return None
    try:
        payload = _decode_bits(region)
    except Exception:
        return None
    parts = payload.split("|")
    if len(parts) != 4:
        return None
    org_id, model, iso_ts, nonce = parts
    try:
        issued_at = datetime.fromisoformat(iso_ts)
    except Exception:
        return None
    return ProvenanceRecord(org_id=org_id, model=model, issued_at=issued_at, nonce=nonce)
