from __future__ import annotations

from datetime import datetime, timezone

from exfilsentinel.models import ProvenanceRecord
from exfilsentinel.watermark import detect, embed, verify

UTC = timezone.utc


def _record(org="acme", model="ft:acme-prod", nonce="abc123"):
    return ProvenanceRecord(org_id=org, model=model,
                            issued_at=datetime(2026, 7, 11, 12, 0, 0, tzinfo=UTC),
                            nonce=nonce)


def test_embed_verify_roundtrip():
    text = "This is a confidential model output that may be leaked."
    wm = embed(text, _record())
    assert wm.text.startswith(text)
    rec = verify(wm.text)
    assert rec is not None
    assert rec.org_id == "acme"
    assert rec.model == "ft:acme-prod"
    assert rec.nonce == "abc123"


def test_detect_true_on_watermarked():
    wm = embed("hello world", _record())
    assert detect(wm.text) is True


def test_detect_false_on_clean_text():
    assert detect("hello world, this is normal text without any watermark.") is False


def test_verify_returns_none_on_clean():
    assert verify("no watermark here") is None


def test_watermark_survives_copy_paste():
    # Simulate copy-paste: take the exact watermarked string (no re-encode).
    wm = embed("Our proprietary synthesis approach is as follows.", _record())
    # Re-read the exact string (as a user would Ctrl+C/V it)
    pasted = wm.text
    rec = verify(pasted)
    assert rec is not None
    assert rec.nonce == "abc123"


def test_unicode_payload_roundtrip():
    rec = ProvenanceRecord(org_id="org-é", model="mödel/x", issued_at=datetime(2026,7,11,0,0,tzinfo=UTC), nonce="nz_9")
    wm = embed("data", rec)
    got = verify(wm.text)
    assert got.org_id == "org-é"
    assert got.model == "mödel/x"
    assert got.nonce == "nz_9"


def test_detect_rejects_garbage_region():
    # Zero-width noise without a valid PREAMBLE..POSTAMBLE frame is rejected.
    garbage = "​​​‌‌‍‍‍"
    assert detect(garbage) is False
    assert verify(garbage) is None

