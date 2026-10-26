"""Shared test helpers: a fake command runner and small filesystem fixtures."""

from __future__ import annotations

import os
import subprocess
import tempfile


class FakeResult:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class FakeRunner:
    """Maps a command prefix to a canned result. No process is spawned."""

    def __init__(self, table=None, default=None):
        # table: list of (prefix_tuple, FakeResult) checked in order
        self.table = list(table or [])
        self.default = default if default is not None else FakeResult(
            127, "", "command not found"
        )
        self.calls = []

    def run(self, argv, timeout=10.0, cwd=None):
        self.calls.append(tuple(argv))
        for prefix, result in self.table:
            if tuple(argv[: len(prefix)]) == tuple(prefix):
                return result
        return self.default


class TmpTree:
    """Context manager yielding a temp dir, cleaned up by the OS scratch prune."""

    def __init__(self):
        self._dir = None

    def __enter__(self):
        self._dir = tempfile.mkdtemp(prefix="decoderattest-test-")
        return self._dir

    def __exit__(self, *exc):
        return False


def write(path, text):
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)
    return path


def rule_doc():
    """A minimal but shape-real rule document, mirroring the shipped schema."""
    return {
        "rule_version": 1,
        "advisory": {
            "id": "CVE-2099-0001",
            "aliases": ["GHSA-test"],
            "url": "https://example.invalid/",
            "summary": "test rule",
        },
        "products": [
            {
                "id": "node",
                "ecosystem": "node",
                "package": "node",
                "kind": "runtime_lines",
                "lines": {"22": "22.23.4", "24": "24.22.1", "26": "26.12.1"},
                "eol_note": "unfixed lines",
                "note": "Node.js ships a bundled copy of the decoder; the system "
                        "libbrotli version does not apply to this runtime.",
            },
            {
                "id": "py-brotli",
                "ecosystem": "python",
                "package": "Brotli",
                "kind": "range",
                "affected": [{"min": "1.0.3", "max": "1.2.0"}],
                "fixed": ["1.0.10", "1.1.1", "1.2.1"],
                "note": "fixed list wins inside the span",
            },
            {
                "id": "sys-brotli",
                "ecosystem": "system",
                "package": "libbrotli",
                "packages": ["libbrotli1", "libbrotlidec1", "brotli"],
                "kind": "range",
                "affected": [{"min": "1.0.3", "max_exclusive": "1.2.1"}],
                "fixed": ["1.0.10", "1.1.1", "1.2.1"],
            },
        ],
    }


VERSION_H = """\
#ifndef BROTLI_COMMON_VERSION_H_
#define BROTLI_COMMON_VERSION_H_
#define BROTLI_MAKE_HEX_VERSION(A, B, C) ((A << 24) | (B << 12) | C)
#define BROTLI_VERSION_MAJOR {major}
#define BROTLI_VERSION_MINOR {minor}
#define BROTLI_VERSION_PATCH {patch}
#define BROTLI_VERSION BROTLI_MAKE_HEX_VERSION(                     \\
  BROTLI_VERSION_MAJOR, BROTLI_VERSION_MINOR, BROTLI_VERSION_PATCH)
#endif
"""

DECODE_H_PATCHED = """\
#ifndef BROTLI_DEC_DECODE_H_
#define BROTLI_DEC_DECODE_H_
#define BROTLI_ERROR_CODE(CATEGORY, NAME, CODE) CATEGORY##NAME = CODE
#define BROTLI_ERROR_CODES_LIST(BROTLI_ERROR_CODE, SEPARATOR)              \\
  BROTLI_ERROR_CODE(_ERROR_FORMAT_, EXUBERANT_NIBBLE, -1) SEPARATOR        \\
  BROTLI_ERROR_CODE(_ERROR_FORMAT_, BLOCK_SWITCH, -17) SEPARATOR
#endif
"""

DECODE_H_UNPATCHED = """\
#ifndef BROTLI_DEC_DECODE_H_
#define BROTLI_DEC_DECODE_H_
#define BROTLI_ERROR_CODE(CATEGORY, NAME, CODE) CATEGORY##NAME = CODE
#define BROTLI_ERROR_CODES_LIST(BROTLI_ERROR_CODE, SEPARATOR)              \\
  BROTLI_ERROR_CODE(_ERROR_FORMAT_, EXUBERANT_NIBBLE, -1) SEPARATOR
#endif
"""


def make_vendored_tree(root, version=(1, 2, 0), patched=False, with_version_h=True):
    """Build a realistic vendored layout: c/include/brotli/decode.h + c/common/version.h."""
    base = os.path.join(root, "third_party", "brotli", "c")
    write(
        os.path.join(base, "include", "brotli", "decode.h"),
        DECODE_H_PATCHED if patched else DECODE_H_UNPATCHED,
    )
    if with_version_h:
        write(
            os.path.join(base, "common", "version.h"),
            VERSION_H.format(major=version[0], minor=version[1], patch=version[2]),
        )
    return base


def unused_import_guard():
    """Keeps flake-shaped linters quiet about the subprocess import."""
    return subprocess.__name__
