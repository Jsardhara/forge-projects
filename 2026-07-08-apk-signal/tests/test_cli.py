"""Smoke tests for the apk-signal CLI."""

import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from apk_signal.__main__ import main


def _make_apk(path: Path) -> None:
    manifest = (
        "<manifest package='com.test.cli'>"
        "<uses-permission android:name='android.permission.INTERNET'/>"
        "</manifest>"
    )
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("AndroidManifest.xml", manifest)
        zf.writestr("classes.dex", b"benign code here")


def test_cli_report(tmp_path, capsys):
    apk = tmp_path / "app.apk"
    _make_apk(apk)
    rc = main([str(apk)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "APK SIGNAL REPORT" in out
    assert "com.test.cli" in out


def test_cli_json(tmp_path, capsys):
    apk = tmp_path / "app.apk"
    _make_apk(apk)
    rc = main([str(apk), "--json"])
    assert rc == 0
    import json
    data = json.loads(capsys.readouterr().out)
    assert data["package_name"] == "com.test.cli"
    assert "signals" in data


def test_cli_missing_file(tmp_path, capsys):
    rc = main([str(tmp_path / "missing.apk")])
    assert rc == 2
    assert "not found" in capsys.readouterr().err.lower()
