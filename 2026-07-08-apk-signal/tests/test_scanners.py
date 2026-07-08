"""Tests for apk_signal.scanners — network, secrets, capabilities, permissions."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from apk_signal.scanners import (
    scan_capabilities,
    scan_network,
    scan_secrets,
    score_permission,
)
from apk_signal.models import SignalType, Severity


def test_scan_network_finds_url():
    text = "check http://evil-c2.example.com/beacon and also https://update.foo.net/x"
    sigs = scan_network(text, "classes.dex")
    assert any("http://evil-c2.example.com/beacon" in s.detail for s in sigs)
    assert any("https://update.foo.net/x" in s.detail for s in sigs)
    assert all(s.signal_type == SignalType.NETWORK_INDICATOR for s in sigs)


def test_scan_network_finds_ipv4():
    text = "connect to 185.220.101.45 now"
    sigs = scan_network(text, "x")
    assert any(s.detail == "185.220.101.45" for s in sigs)


def test_scan_network_rejects_bad_octet():
    text = "not an ip 999.1.1.1 here"
    sigs = scan_network(text, "x")
    assert all(s.detail != "999.1.1.1" for s in sigs)


def test_scan_secrets_aws_key():
    text = "cfg awsKey=AKIAIOSFODNN7EXAMPLE1"
    sigs = scan_secrets(text, "x")
    assert any(s.label == "AWS Access Key ID" for s in sigs)
    assert any(s.severity == Severity.CRITICAL for s in sigs)


def test_scan_secrets_stripe_live():
    text = "sk_live_abc123DEF456ghi789"
    sigs = scan_secrets(text, "x")
    assert any(s.label == "Stripe Secret Key" for s in sigs)


def test_scan_secrets_pem_private_key():
    text = "embedded -----BEGIN RSA PRIVATE KEY-----"
    sigs = scan_secrets(text, "x")
    assert any("PEM Private Key" in s.label for s in sigs)


def test_scan_secrets_negation_no_false_positive():
    # "api_key" mentioned but negated context -> generic key should NOT fire
    text = "this library does not use an api_key like 'supersecretvalue123'"
    sigs = scan_secrets(text, "x")
    assert not any(s.label == "Generic API Key assignment" for s in sigs)


def test_scan_capabilities_credential_theft():
    text = "this module will steal passwords from the victim"
    sigs = scan_capabilities(text, "x")
    assert any("credential" in s.label.lower() or "theft" in s.label.lower() for s in sigs)
    assert any(s.severity == Severity.CRITICAL for s in sigs)


def test_scan_capabilities_negation():
    text = "our app does not steal credentials and is safe"
    sigs = scan_capabilities(text, "x")
    assert not any("credential" in s.label.lower() or "theft" in s.label.lower() for s in sigs)


def test_scan_capabilities_accessibility():
    text = "register android.accessibilityservice to read screen"
    sigs = scan_capabilities(text, "x")
    assert any("Accessibility" in s.label for s in sigs)


def test_score_permission_known():
    sev, score = score_permission("android.permission.BIND_ACCESSIBILITY_SERVICE")
    assert sev == Severity.HIGH
    assert score == 15


def test_score_permission_unknown_custom():
    res = score_permission("com.evil.thing.CUSTOM_ACTION")
    assert res is not None
    assert res[0] == Severity.LOW


def test_score_permission_benign():
    assert score_permission("android.permission.INTERNET") == (Severity.INFO, 0)
