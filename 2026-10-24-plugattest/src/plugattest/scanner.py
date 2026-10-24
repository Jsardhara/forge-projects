"""Detect what a package's own source *actually does*.

Scope discipline: only the package's own code is scanned. Vendored trees
(``node_modules``, ``site-packages``, ``vendor``), VCS internals, caches and build
output are skipped -- a dependency's capabilities are the dependency's to declare.
Documentation is skipped too: prose that mentions ``subprocess.run`` is not a call.
"""

import os
import re
from dataclasses import dataclass

CODE_SUFFIXES = (".py", ".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx",
                 ".sh", ".bash", ".zsh")

SKIP_DIRS = {
    ".git", ".hg", ".svn", "node_modules", "site-packages", "vendor",
    "__pycache__", ".venv", "venv", ".mypy_cache", ".pytest_cache",
    ".ruff_cache", "dist", "build", ".tox", "htmlcov",
}

# A package manager install both reaches the network and executes a resolver.
_PKG_INSTALL_RE = r"\b(npm|pnpm|yarn|pip3?|apt|apt-get|brew)\s+(install|i|add)\b"

# capability -> ((signal label, compiled pattern), ...)
_SIGNALS = {
    "shell": (
        ("subprocess", re.compile(r"subprocess\.(run|Popen|call|check_output|check_call)")),
        ("os.system", re.compile(r"os\.system\s*\(")),
        ("os.popen", re.compile(r"os\.popen\s*\(")),
        ("child_process", re.compile(r"child_process")),
        ("node-exec-sync", re.compile(r"\b(execSync|spawnSync)\s*\(")),
        ("runtime-exec", re.compile(r"Runtime\.getRuntime\(\)\.exec")),
        ("invoke-webrequest", re.compile(r"Invoke-Expression")),
        ("package-install", re.compile(_PKG_INSTALL_RE)),
    ),
    "network": (
        ("urlopen", re.compile(r"urlopen\s*\(")),
        ("urllib", re.compile(r"urllib\.request")),
        ("requests", re.compile(r"\brequests\.(get|post|put|patch|delete|Session)\s*\(")),
        ("httpx-aiohttp", re.compile(r"\b(httpx|aiohttp)\b")),
        ("http-client", re.compile(r"http\.client")),
        ("socket", re.compile(r"\bsocket\.(socket|create_connection)\s*\(")),
        ("fetch", re.compile(r"\bfetch\s*\(")),
        ("axios", re.compile(r"\baxios\b")),
        ("curl", re.compile(r"\b(curl|wget)\s+\S")),
        ("package-install", re.compile(_PKG_INSTALL_RE)),
        ("http-server", re.compile(r"-m\s+http\.server\b|\bhttp\.server\s+\d")),
        ("net-connect", re.compile(r"\bnet\.connect\s*\(")),
    ),
    "credentials": (
        ("env-read", re.compile(r"os\.(environ|getenv)")),
        ("node-env", re.compile(r"process\.env")),
        ("ssh-key", re.compile(r"\.ssh/|id_rsa|id_ed25519")),
        ("aws-creds", re.compile(r"\.aws/credentials|AWS_SECRET_ACCESS_KEY")),
        ("netrc", re.compile(r"\.netrc")),
        ("keychain", re.compile(r"\bkeyring\.|security find-generic-password")),
        ("dotenv", re.compile(r"dotenv|\bos\.environ\[")),
    ),
    "fs_write": (
        ("python-open-write", re.compile(r"open\s*\([^)]*,\s*[\"'][wax]")),
        ("write-text", re.compile(r"\.write_(text|bytes)\s*\(")),
        ("node-write", re.compile(r"\b(writeFileSync|writeFile|appendFileSync|appendFile)\s*\(")),
        ("node-remove", re.compile(r"\b(unlinkSync|rmSync|rmdirSync|rmdir)\s*\(")),
        ("shutil-destructive", re.compile(r"shutil\.(rmtree|move|copy)")),
        ("os-remove", re.compile(r"os\.(remove|unlink|rmdir|rename)\s*\(")),
        ("chmod", re.compile(r"os\.chmod\s*\(")),
    ),
    "code_eval": (
        ("eval", re.compile(r"\beval\s*\(")),
        ("exec", re.compile(r"\bexec\s*\(")),
        ("new-function", re.compile(r"new\s+Function\s*\(")),
        ("pickle", re.compile(r"pickle\.loads?\s*\(")),
        ("yaml-load", re.compile(r"yaml\.load\s*\(")),
        ("compile", re.compile(r"\bcompile\s*\(")),
    ),
}


@dataclass(frozen=True)
class CapabilityHit:
    """A capability observed in the package's own code."""

    capability: str
    path: str
    line: int
    signal: str


def _iter_source_files(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for name in sorted(filenames):
            if name.endswith(CODE_SUFFIXES):
                yield os.path.join(dirpath, name)


def _read_lines(path):
    try:
        with open(path, "r", encoding="utf-8", errors="strict") as handle:
            return handle.read().splitlines()
    except (UnicodeDecodeError, OSError):
        return None  # binary or unreadable: not source we can attest


def scan_package(root):
    """Return one CapabilityHit per (file, capability), sorted deterministically."""
    if not os.path.isdir(root):
        raise OSError("package directory not found: %s" % root)

    hits = []
    seen = set()
    for path in _iter_source_files(root):
        lines = _read_lines(path)
        if lines is None:
            continue
        relative = os.path.relpath(path, root)
        for capability in sorted(_SIGNALS):
            if (relative, capability) in seen:
                continue
            for line_number, line in enumerate(lines, start=1):
                matched = _first_signal(capability, line)
                if matched:
                    hits.append(CapabilityHit(capability, relative, line_number, matched))
                    seen.add((relative, capability))
                    break
    return hits


def _first_signal(capability, line):
    for label, pattern in _SIGNALS[capability]:
        if pattern.search(line):
            return label
    return None
