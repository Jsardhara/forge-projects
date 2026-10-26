"""Vendored decoder discovery and two-signal attestation.

Many projects ship a private copy of Google's C Brotli decoder instead of linking
the system library, so a distribution update fixes nothing for them. A vendored
copy carries two independent pieces of evidence about whether it is patched:

1. the declared version macros in ``common/version.h``;
2. the ``BLOCK_SWITCH`` error code, which the fix introduced in ``decode.h``.

A version can be bumped by a build script, and a header can be a stale remnant of
an older tree, so neither signal is sufficient alone. When they disagree the copy
is reported as UNKNOWN rather than resolved in the safe direction -- a certification
of safety that cannot be shown to be true is the exact failure this tool exists to
avoid.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import List, Optional

__all__ = ["VendoredCopy", "scan_tree", "FIX_INTRODUCED_BLOCK_SWITCH"]

#: First upstream release whose decoder carries the BLOCK_SWITCH error code.
FIX_INTRODUCED_BLOCK_SWITCH = "1.2.1"

_MAJOR = re.compile(r"#\s*define\s+BROTLI_VERSION_MAJOR\s+(\d+)")
_MINOR = re.compile(r"#\s*define\s+BROTLI_VERSION_MINOR\s+(\d+)")
_PATCH = re.compile(r"#\s*define\s+BROTLI_VERSION_PATCH\s+(\d+)")
_BLOCK_SWITCH = re.compile(r"BLOCK_SWITCH")

_SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv"}
_MAX_DEPTH = 14


@dataclass(frozen=True)
class VendoredCopy:
    header: str
    version: Optional[str]
    has_block_switch: bool
    signals_agree: bool
    version_file: Optional[str] = None


def scan_tree(root: str, max_depth: int = _MAX_DEPTH) -> List[VendoredCopy]:
    """Find every ``brotli/decode.h`` under ``root`` and read its two signals."""
    if not os.path.isdir(root):
        raise OSError("vendor path is not a directory: %s" % root)
    copies: List[VendoredCopy] = []
    root_depth = root.rstrip(os.sep).count(os.sep)
    for current, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(name for name in dirnames if name not in _SKIP_DIRS)
        if current.count(os.sep) - root_depth >= max_depth:
            dirnames[:] = []
        if "decode.h" not in filenames:
            continue
        if os.path.basename(current) != "brotli":
            continue
        copies.append(_inspect(os.path.join(current, "decode.h")))
    return copies


def _inspect(header: str) -> VendoredCopy:
    header_text = _read(header)
    has_marker = bool(_BLOCK_SWITCH.search(header_text))
    version, version_file = _read_version(header)
    agree = _agree(version, has_marker)
    return VendoredCopy(
        header=header,
        version=version,
        has_block_switch=has_marker,
        signals_agree=agree,
        version_file=version_file,
    )


def _read_version(header: str):
    """Walk up from the header looking for a version.h describing this tree."""
    directory = os.path.dirname(header)
    for _ in range(4):
        for candidate in (
            os.path.join(directory, "..", "common", "version.h"),
            os.path.join(directory, "version.h"),
        ):
            candidate = os.path.normpath(candidate)
            if not os.path.isfile(candidate):
                continue
            text = _read(candidate)
            major = _MAJOR.search(text)
            minor = _MINOR.search(text)
            patch = _PATCH.search(text)
            if major and minor and patch:
                return (
                    "%s.%s.%s" % (major.group(1), minor.group(1), patch.group(1)),
                    candidate,
                )
        parent = os.path.dirname(directory)
        if parent == directory:
            break
        directory = parent
    return None, None


def _agree(version: Optional[str], has_marker: bool) -> bool:
    """Two signals are consistent iff the marker appears exactly when version says it should."""
    if version is None:
        # Only one signal exists; there is nothing for it to contradict.
        return True
    declared_fixed = _at_least_fix(version)
    return declared_fixed == has_marker


def _at_least_fix(version: str) -> bool:
    from .version import VersionError, compare

    try:
        return compare(version, FIX_INTRODUCED_BLOCK_SWITCH) >= 0
    except VersionError:
        return False


def _read(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            return handle.read()
    except OSError:
        return ""
