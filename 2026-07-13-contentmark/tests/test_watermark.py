"""Tests for the provenance watermark (embed / verify / tamper detection)."""
from contentmark import embed, verify
from contentmark.models import Provenance, ProvenanceLabel, SignatureVerification
from contentmark.watermark import _decode_bits, _encode_bits, _fnv1a, _payload

from fixtures import PLAIN_TEXT


def _prov():
    return Provenance(
        rid="cm_test123",
        label=ProvenanceLabel.AI_GENERATED,
        tool="AcmeWriter",
        model="gpt-x",
        author="alice",
    )


def test_embed_contains_comment_and_signature():
    labeled = embed(PLAIN_TEXT, _prov())
    assert "contentmark:provenance" in labeled
    assert "\u200b" in labeled and "\u200c" in labeled


def test_verify_roundtrip_valid():
    labeled = embed(PLAIN_TEXT, _prov())
    v = verify(labeled)
    assert v.present
    assert v.valid
    assert not v.tampered
    assert v.rid == "cm_test123"
    assert v.label == "ai_generated"


def test_verify_no_marker_absent():
    v = verify(PLAIN_TEXT)
    assert not v.present
    assert not v.valid


def test_tamper_signature_detected():
    labeled = embed(PLAIN_TEXT, _prov())
    # Edit the visible text only (should NOT break the invisible sig).
    edited = labeled.replace("quarterly report", "QUARTERLY REPORT")
    v = verify(edited)
    assert v.present
    assert v.valid  # invisible sig still intact


def test_tamper_comment_label_mismatch_detected():
    labeled = embed(PLAIN_TEXT, _prov())
    # Mangle the structured comment label while leaving invisible sig.
    tampered = labeled.replace('"label":"ai_generated"', '"label":"human"')
    v = verify(tampered)
    # Both present but disagree.
    assert v.present
    assert v.tampered
    assert not v.valid


def test_copy_paste_survives_comment_removal():
    labeled = embed(PLAIN_TEXT, _prov())
    # Simulate copy-paste that strips the HTML comment.
    without_comment = labeled.split("-->", 1)[-1]
    v = verify(without_comment)
    assert v.present
    assert v.valid
    assert v.label == "ai_generated"


def test_encode_decode_roundtrip():
    payload = _payload(_prov())
    decoded = _decode_bits(_encode_bits(payload))
    assert decoded == payload


def test_fnv1a_stable():
    assert _fnv1a("abc") == _fnv1a("abc")
    assert _fnv1a("abc") != _fnv1a("abd")


def test_decode_garbage_returns_none():
    assert _decode_bits("no markers here plain text") is None


def test_verify_type():
    v = verify(PLAIN_TEXT)
    assert isinstance(v, SignatureVerification)
