"""Invisible provenance watermark + structured provenance for contentmark.

Technique lineage: copy-paste-surviving invisible signature using four
zero-width Unicode characters, with strict role separation to avoid the
delimiter/bit collision that was fixed in exfilsentinel (2026-07-11):
  - framing only:  ZWSP (U+200B) start, ZWNJ (U+200C) end
  - data bits only: ZWJ (U+200D) = 1, WORD-JOINER (U+2060) = 0

No delimiters are reused across roles, so a 0-bit can never be mistaken for
framing. A FNV-1a checksum is embedded so tampering is detectable.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict
from typing import Optional

from .models import Provenance, ProvenanceLabel, SignatureVerification

# Zero-width characters (kept as raw codepoints to avoid source-file maskers)
ZWSP = "\u200b"          # framing start
ZWNJ = "\u200c"          # framing end
ZWJ = "\u200d"           # bit 1
WJ = "\u2060"            # bit 0 (WORD JOINER)
MAGIC = "CM1"

_COMMENT_RE = re.compile(
    r"<!--\s*contentmark:provenance\s*(\{.*?\})\s*-->", re.DOTALL
)


def _fnv1a(s: str) -> str:
    h = 0x811C9DC5
    for ch in s.encode("utf-8"):
        h ^= ch
        h = (h * 0x01000193) & 0xFFFFFFFF
    return format(h, "08x")


def _payload(prov: Provenance) -> str:
    d = asdict(prov)
    d["generated_at"] = prov.generated_at.isoformat()
    canonical = json.dumps(d, separators=(",", ":"), sort_keys=True)
    return f"{MAGIC}{canonical}|{_fnv1a(canonical)}"


def _encode_bits(payload: str) -> str:
    bits: list[str] = []
    for byte in payload.encode("utf-8"):
        for i in range(7, -1, -1):
            bits.append(ZWJ if (byte >> i) & 1 else WJ)
    return ZWSP + "".join(bits) + ZWNJ


def _decode_bits(sig: str) -> Optional[str]:
    # Find frame start/end; collect only bit chars between them.
    start = sig.find(ZWSP)
    if start == -1:
        return None
    end = sig.find(ZWNJ, start + 1)
    if end == -1:
        return None
    inner = sig[start + 1 : end]
    bit_chars = [c for c in inner if c in (ZWJ, WJ)]
    if not bit_chars:
        return None
    bits = "".join("1" if c == ZWJ else "0" for c in bit_chars)
    if len(bits) % 8 != 0:
        return None
    out = bytearray()
    for i in range(0, len(bits), 8):
        byte = int(bits[i : i + 8], 2)
        out.append(byte)
    try:
        text = out.decode("utf-8")
    except UnicodeDecodeError:
        return None
    if not text.startswith(MAGIC):
        return None
    return text


def _provenance_from_payload(payload: str) -> Optional[Provenance]:
    body, _, chk = payload[len(MAGIC) :].rpartition("|")
    try:
        d = json.loads(body)
    except json.JSONDecodeError:
        return None
    if _fnv1a(body) != chk:
        return None
    return Provenance.from_dict(d)


def provenance_to_comment(prov: Provenance) -> str:
    d = asdict(prov)
    d["generated_at"] = prov.generated_at.isoformat()
    return f"<!-- contentmark:provenance {json.dumps(d, separators=(',', ':'))} -->"


def embed(text: str, prov: Provenance) -> str:
    """Return text with an embedded structured provenance comment + invisible signature."""
    comment = provenance_to_comment(prov)
    sig = _encode_bits(_payload(prov))
    body = text.rstrip()
    if not body:
        body = text
    return f"{body}\n{comment}\n{sig}\n"


def _parse_comment(text: str) -> Optional[Provenance]:
    m = _COMMENT_RE.search(text)
    if not m:
        return None
    try:
        d = json.loads(m.group(1))
    except json.JSONDecodeError:
        return None
    try:
        return Provenance.from_dict(d)
    except (KeyError, ValueError):
        return None


def verify(text: str) -> SignatureVerification:
    comment_prov = _parse_comment(text)
    decoded = _decode_bits(text)
    sig_prov = _provenance_from_payload(decoded) if decoded else None

    present = comment_prov is not None or sig_prov is not None
    if not present:
        return SignatureVerification(
            present=False, valid=False, tampered=False, detail="no provenance marker found"
        )

    if sig_prov is None and comment_prov is not None:
        return SignatureVerification(
            present=True,
            valid=True,
            tampered=False,
            rid=comment_prov.rid,
            label=comment_prov.label.value,
            detail="structured comment present; invisible signature absent",
        )
    if sig_prov is not None and comment_prov is None:
        return SignatureVerification(
            present=True,
            valid=True,
            tampered=False,
            rid=sig_prov.rid,
            label=sig_prov.label.value,
            detail="invisible signature present; structured comment absent",
        )

    # Both present — they must agree.
    agree = (
        comment_prov.rid == sig_prov.rid
        and comment_prov.label == sig_prov.label
    )
    return SignatureVerification(
        present=True,
        valid=agree,
        tampered=not agree,
        rid=sig_prov.rid,
        label=sig_prov.label.value,
        detail=("comment and signature agree" if agree else "comment and signature DISAGREE"),
    )
