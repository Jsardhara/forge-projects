"""Tests for apk_signal.analyzer — end-to-end on a synthetic APK (real ZIP)."""

import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from apk_signal.analyzer import analyze


def _build_malicious_apk(path: Path) -> None:
    manifest = (
        "<?xml version='1.0' encoding='utf-8'?>"
        "<manifest package='com.evil.spyware' "
        "android:minSdkVersion='21' android:targetSdkVersion='33'>"
        "<uses-permission android:name='android.permission.INTERNET'/>"
        "<uses-permission android:name='android.permission.READ_SMS'/>"
        "<uses-permission android:name='android.permission.RECEIVE_SMS'/>"
        "<uses-permission android:name='android.permission.BIND_ACCESSIBILITY_SERVICE'/>"
        "<uses-permission android:name='android.permission.SYSTEM_ALERT_WINDOW'/>"
        "<uses-permission android:name='android.permission.REQUEST_INSTALL_PACKAGES'/>"
        "<uses-permission android:name='android.permission.BIND_DEVICE_ADMIN'/>"
        "</manifest>"
    )
    classes = (
        b"some smali code that will steal passwords from the victim\n"
        b"connect to http://evil-c2.example.com/beacon?uid=42\n"
        b"api_key = 'AKIAIOSFODNN7EXAMPLE'\n"
        b"intercept sms and forward to 185.220.101.45\n"
        b"overlay window to phish banking login\n"
    )
    lib = b"\x7fELF\x01\x01\x01 fake native lib bytes"
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("AndroidManifest.xml", manifest)
        zf.writestr("classes.dex", classes)
        zf.writestr("classes2.dex", b"secondary dex with wallet targeting code")
        zf.writestr("lib/arm64-v8a/libnative.so", lib)


def test_analyze_malicious_apk(tmp_path):
    apk = tmp_path / "evil.apk"
    _build_malicious_apk(apk)
    result = analyze(str(apk))

    assert result.package_name == "com.evil.spyware"
    assert result.entry_count >= 4
    assert result.dex_count >= 2
    assert "android.permission.READ_SMS" in result.permissions
    assert "android.permission.BIND_ACCESSIBILITY_SERVICE" in result.permissions

    labels = [s.label for s in result.signals]
    # secrets
    assert any("AWS Access Key ID" in l for l in labels)
    # network
    assert any("evil-c2.example.com" in s.detail for s in result.signals)
    assert any(s.detail == "185.220.101.45" for s in result.signals)
    # capability
    assert any("credential" in l.lower() or "theft" in l.lower() for l in labels)
    # permission signals
    assert any(s.signal_type.value == "permission" for s in result.signals)
    # native + multidex
    assert any(s.label == "Native libraries present" for s in result.signals)
    assert any(s.label == "Multi-dex application" for s in result.signals)

    # Risk should be high given the mix
    assert result.risk_score >= 40
    assert result.risk_level in (result.risk_level.CRITICAL, result.risk_level.HIGH)


def test_analyze_benign_apk(tmp_path):
    apk = tmp_path / "clean.apk"
    manifest = (
        "<?xml version='1.0' encoding='utf-8'?>"
        "<manifest package='com.example.notes'>"
        "<uses-permission android:name='android.permission.INTERNET'/>"
        "<uses-permission android:name='android.permission.ACCESS_NETWORK_STATE'/>"
        "</manifest>"
    )
    with zipfile.ZipFile(apk, "w") as zf:
        zf.writestr("AndroidManifest.xml", manifest)
        zf.writestr("classes.dex", b"harmless app code, no malicious strings here")
    result = analyze(str(apk))
    # Only INTERNET / ACCESS_NETWORK_STATE -> both INFO, score 0
    assert result.risk_score == 0
    assert result.risk_level == result.risk_level.INFO
    assert result.package_name == "com.example.notes"


def test_analyze_missing_file(tmp_path):
    import pytest
    with pytest.raises(FileNotFoundError):
        analyze(str(tmp_path / "nope.apk"))
