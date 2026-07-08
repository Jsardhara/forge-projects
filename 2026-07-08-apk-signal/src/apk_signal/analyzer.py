"""APK analysis orchestrator for apk-signal.

An APK is a ZIP. We never decompile — we scan raw entry bytes decoded as
latin-1 (lossless, no decode errors) for strings. The AndroidManifest.xml
carries permissions and package metadata in its string pool; for the binary
XML we use a tolerant substring scan so we don't need a full AXML parser.
"""

from __future__ import annotations

import zipfile
from pathlib import Path
from typing import List

from .models import AnalysisResult, Severity, Signal, SignalType
from .scanners import (
    scan_capabilities,
    scan_network,
    scan_secrets,
    score_permission,
)

# Entry names we skip scanning entirely (binary assets with no useful strings).
_SKIP_SUFFIXES = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".mp3", ".wav",
                  ".ttf", ".otf", ".so", ".odex", ".vdex", ".arsc")


def _should_scan(name: str) -> bool:
    low = name.lower()
    if low.endswith(_SKIP_SUFFIXES):
        return False
    # Skip large resources we won't find strings in except manifest/xml/properties
    if low.endswith(".xml") or low.endswith(".properties") or low.endswith(".txt"):
        return True
    return True  # classes*.dex, lib/*.so strings, assets/* all scanned as text


def _extract_permissions(text: str) -> List[str]:
    """Pull android.permission.* and custom permission names from manifest text."""
    perms: List[str] = []
    import re
    for m in re.finditer(r"android\.permission\.[A-Z_]+", text):
        perms.append(m.group(0))
    # Custom permission style: com.foo.permission.SOMETHING
    for m in re.finditer(r"\b(?:[a-z0-9](?:[a-z0-9.])*)\.permission\.[A-Z_]+", text):
        v = m.group(0)
        if not v.startswith("android.permission"):
            perms.append(v)
    # de-dup preserve order
    seen = set()
    out = []
    for p in perms:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def _scan_entry(name: str, data: bytes) -> List[Signal]:
    """Decode entry bytes and run all scanners. Latin-1 is lossless for bytes."""
    try:
        text = data.decode("latin-1")
    except Exception:
        return []
    out: List[Signal] = []
    out.extend(scan_network(text, name))
    out.extend(scan_secrets(text, name))
    out.extend(scan_capabilities(text, name))
    return out


def analyze(apk_path: str) -> AnalysisResult:
    path = Path(apk_path)
    result = AnalysisResult(apk_path=str(path))

    if not path.is_file():
        raise FileNotFoundError(f"APK not found: {apk_path}")

    with zipfile.ZipFile(path, "r") as zf:
        names = zf.namelist()
        result.entry_count = len(names)
        # Structure signals
        dex_count = sum(1 for n in names if n.startswith("classes") and n.endswith(".dex"))
        result.dex_count = dex_count
        native_libs = [n for n in names if n.endswith(".so")]
        result.native_libs = native_libs

        manifest_text = ""
        for info in zf.infolist():
            name = info.filename
            if name.lower().endswith("androidmanifest.xml"):
                try:
                    manifest_text = zf.read(info).decode("latin-1", errors="replace")
                except Exception:
                    manifest_text = ""
                continue

        # Scan every entry we care about, EXCEPT the manifest (its string pool is
        # only used for permission/package extraction below — generic scanning of it
        # produces false-positive "network indicators" from package/class names).
        for info in zf.infolist():
            name = info.filename
            if name.lower().endswith("androidmanifest.xml"):
                continue
            if not _should_scan(name):
                continue
            try:
                data = zf.read(info)
            except Exception:
                continue
            # Size guard: skip enormous entries to keep memory bounded
            if len(data) > 5_000_000:
                continue
            result.signals.extend(_scan_entry(name, data))

        # Permissions from manifest
        perms = _extract_permissions(manifest_text)
        result.permissions = perms
        for perm in perms:
            scored = score_permission(perm)
            if scored is None:
                continue
            sev, score = scored
            result.signals.append(Signal(
                signal_type=SignalType.PERMISSION,
                severity=sev,
                label="Permission",
                detail=perm,
                evidence=perm,
                source_file="AndroidManifest.xml",
                score=score,
            ))

        # Package name + SDK from manifest string pool
        import re
        pm = re.search(r"(?:[a-z0-9](?:[a-z0-9_.\-]){2,})\.(?:[a-z0-9](?:[a-z0-9_.\-]){1,})", manifest_text)
        if pm:
            candidate = pm.group(0)
            if candidate.count(".") >= 1 and not candidate.startswith("android.permission"):
                result.package_name = candidate

        # Native lib + multi-dex structural signals
        if native_libs:
            result.signals.append(Signal(
                signal_type=SignalType.NATIVE_LIB,
                severity=Severity.LOW,
                label="Native libraries present",
                detail=f"{len(native_libs)} native lib(s): " + ", ".join(sorted(set(native_libs))[:5]),
                source_file=", ".join(native_libs[:3]),
                score=3,
            ))
        if dex_count > 1:
            result.signals.append(Signal(
                signal_type=SignalType.STRUCTURE,
                severity=Severity.LOW,
                label="Multi-dex application",
                detail=f"{dex_count} dex files",
                source_file="classes*.dex",
                score=2,
            ))

    return result
